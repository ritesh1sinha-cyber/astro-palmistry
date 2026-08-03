#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extended Moonology tables from full OCR (Ch.3-10, appendices). Source: rules44."""
from __future__ import annotations

from datetime import date
from typing import Any

# Ch.4 - top 5 New Moon themes per sign (monthly lunation flavour)
NEW_MOON_IN_SIGN: dict[str, list[str]] = {
    "Aries": [
        "Take action - dreams need a clean slate and bold starts.",
        "Make a 12-month plan for self, couple, and work.",
        "Wish for courage if you have been too timid.",
        "Schedule more fun and spontaneity.",
        "Focus on yourself - wardrobe, image, or one personal makeover.",
    ],
    "Taurus": [
        "Make a financial plan - savings, cash flow, and self-worth.",
        "List top 5 values and align daily life with them.",
        "Relax sensually - massage, good food, unhurried comfort.",
        "Check stubborn or lazy habits; adjust gently.",
        "Persevere slowly toward one material or professional goal.",
    ],
    "Gemini": [
        "Communicate honestly - say what you feel, listen well.",
        "Promise yourself mental downtime or daily meditation.",
        "Socialize lightly - polish small talk and networking.",
        "Reach out to siblings, neighbours, or your must-call list.",
        "Start or refresh a reading list; order books and read.",
    ],
    "Cancer": [
        "Family time - resolve tension with nearest and dearest.",
        "Drop insecurity barriers; soften the crab shell.",
        "Nurture self and others; cook or host at home.",
        "Mid-year goal review - tweak annual aims.",
        "Take a warm bath or water ritual to unwind.",
    ],
    "Leo": [
        "Celebrate life - show off talents without apology.",
        "Flirt or romance - wine, dine, or playful connection.",
        "Restart a neglected creative outlet.",
        "Practice self-love and confidence, not arrogance.",
        "Indulge someone you love; live a little.",
    ],
    "Virgo": [
        "Inventory life - what works, what needs change.",
        "Be of service at work or home without keeping score.",
        "Start a health routine - diet, sleep, or morning habit.",
        "Ease perfectionism toward self and loved ones.",
        "Organize bills, files, and clutter.",
    ],
    "Libra": [
        "Relate consciously - harmony in key partnerships.",
        "Partner up - sort marriage or business alliance issues.",
        "Negotiate or renegotiate what feels out of balance.",
        "Beautify life - appearance, art, or refined surroundings.",
        "Regain identity if you have merged too much with another.",
    ],
    "Scorpio": [
        "Deepen intimacy safely - honest passion, not obsession.",
        "Review shared finances - salary, debts, wills, joint money.",
        "Make peace with jealousy or shadow feelings.",
        "Breathe through intensity; avoid compulsive bonds.",
        "Drop grudges and emotional baggage.",
    ],
    "Sagittarius": [
        "Book travel or widen horizons literally or mentally.",
        "Study something that expands freedom and opportunity.",
        "Search for meaning - check narrow-minded habits.",
        "Take a measured risk or add fun to a stale routine.",
        "Turn complaints into gratitude - you are blessed.",
    ],
    "Capricorn": [
        "Plan next year goals with mature strategy.",
        "Be ambitious about reputation and long-term aims.",
        "Show kindness - avoid cold Saturnine control.",
        "Release controlling habits toward self or others.",
        "Establish a tradition or thank mentors and team.",
    ],
    "Aquarius": [
        "Detach from drama; use logic where feelings swamp you.",
        "Be your authentic unconventional self.",
        "Invent a solution if you are stuck in a rut.",
        "Give to charity or a collective cause.",
        "Connect with friends, tribe, or community ideals.",
    ],
    "Pisces": [
        "Dream consciously - imagination for good, not fear.",
        "Face secret fears with an honest inventory.",
        "Test intuition - note hunches, tarot, or inner signals.",
        "Seek emotional or spiritual healing if needed.",
        "Surrender - yoga, spiritual practice, trust the flow.",
    ],
}

# Ch.7 - Full Moon in each sign
FULL_MOON_IN_SIGN: dict[str, dict] = {
    "Aries": {
        "energy": "Fiery and rash.",
        "message": "Life is not a race or a competition.",
        "balance": "Your needs vs those of your partner or closest ally.",
        "questions": [
            "Have I been hot-headed, selfish, or argumentative this month?",
            "Have I been going too fast or impulsive?",
            "Have I been brash, blunt, or too competitive?",
            "Have I ignored other people's finer sensibilities?",
            "Have I had enough fun?",
        ],
    },
    "Taurus": {
        "energy": "Earthy and steady.",
        "message": "Re-energize your life.",
        "balance": "Feelings vs what you can practically do about life.",
        "questions": [
            "Have I been lazy or overly self-indulgent?",
            "Have I been too obsessed with money or status symbols?",
            "Have I been stubborn, jealous, or possessive?",
            "Have I been comfort-eating too much?",
            "Have I done enough exercise?",
        ],
    },
    "Gemini": {
        "energy": "Changeable and fickle.",
        "message": "Slow down and be real with people.",
        "balance": "Wanting to know everything vs taking time to really learn.",
        "questions": [
            "Have I been gossipy, superficial, or flighty?",
            "Have I glossed over other people's feelings?",
            "Have I been too restless or quick to change my mind?",
            "Have I been too much of a silver-tongued hustler?",
            "Have I done enough reading to expand my mind?",
        ],
    },
    "Cancer": {
        "energy": "Dependent and possibly needy.",
        "message": "Feel sure of yourself.",
        "balance": "Achievement drive vs quality time at home.",
        "questions": [
            "Have I been insecure, clingy, and no fun?",
            "Have I approached wants sideways instead of head-on?",
            "Have I been sulky, moody, brooding, or manipulative?",
            "Have I been secretive or paranoid?",
            "Have I had enough family time?",
        ],
    },
    "Leo": {
        "energy": "Bright and proud - maybe too proud.",
        "message": "Get back in touch with humility.",
        "balance": "What friends need vs what you need.",
        "questions": [
            "Have I been too self-centred or egotistical?",
            "Have I treated people around me like minions?",
            "Have I been arrogant, vain, pushy, or pompous?",
            "Have I expressed myself creatively enough?",
            "Have I shown myself enough self-love?",
        ],
    },
    "Virgo": {
        "energy": "Finicky and anxious.",
        "message": "Remember the importance of being helpful to others.",
        "balance": "Being down to earth vs allowing yourself to dream.",
        "questions": [
            "Have I been too picky, pedantic, or critical?",
            "Have I been humble to the point of underrating myself?",
            "Have I been of service enough this month?",
            "Have I been worrying and complaining too much?",
            "Have I paid enough attention to necessary details?",
        ],
    },
    "Libra": {
        "energy": "Focused on relationships and partnerships.",
        "message": "Remind yourself to see the beauty in life.",
        "balance": "What you need vs what you do to keep others happy.",
        "questions": [
            "Have I been too concerned with appearance?",
            "Have I neglected my own needs for others?",
            "Have I been too easily influenced or indecisive?",
            "Have I been living through someone else?",
            "Have I spent enough time beautifying my life?",
        ],
    },
    "Scorpio": {
        "energy": "Potentially rather intense.",
        "message": "This is a good time to bring sexy back.",
        "balance": "Over-intensity vs lazy contentment.",
        "questions": [
            "Have I been jealous, vengeful, suspicious, or toxic?",
            "Have I been living from fear rather than joy?",
            "Have I focused on the negative rather than positive?",
            "Have I been cruel or cunning?",
            "Am I having the intimacy I need to feel good?",
        ],
    },
    "Sagittarius": {
        "energy": "Fun; may prompt sighs of relief.",
        "message": "Life is an adventure. Do not stagnate.",
        "balance": "Speaking your mind vs saying far too much.",
        "questions": [
            "Have I been too flippant or careless?",
            "Have I let distraction and boredom win?",
            "Have I been overconfident or too preachy?",
            "Have I been a commitment-phobe?",
            "Have I been seeing the bigger picture?",
        ],
    },
    "Capricorn": {
        "energy": "Repressed and resigned.",
        "message": "Release trying to control everything and everyone.",
        "balance": "Demands of work vs home.",
        "questions": [
            "Have I been ambitious to the point of ruthlessness?",
            "Have I been obsessed with work over personal life?",
            "Have I been too hard on others?",
            "Have I let my head overrule my heart?",
            "Have I been planning my life enough - or too much?",
        ],
    },
    "Aquarius": {
        "energy": "Ushering in change and progress.",
        "message": "It is time to detach and let go. Really.",
        "balance": "Trying to be all things to all people vs real relationships.",
        "questions": [
            "Have I been pragmatic to the point of losing romance?",
            "Have I lived too much in my head, not my heart?",
            "Have I done things my way just for the sake of it?",
            "Have I tried too hard to befriend people for wrong reasons?",
            "Have I allowed myself to move forwards this month?",
        ],
    },
    "Pisces": {
        "energy": "Nostalgic and a little yearning.",
        "message": "Super mystical Moon - connect with inner psychic.",
        "balance": "Inner peace vs all your duties.",
        "questions": [
            "Have I been dreamy to the point of silly errors?",
            "Have I been overly sensitive and easily hurt?",
            "Have I been acting like a martyr or too easily led?",
            "Have I meditated daily - and if not, why not?",
            "Have I followed dreams, hunches, and intuition?",
        ],
    },
}

from lunation_timing import (
    compute_lunation_timing,
    is_full_moon_applicable,
    is_new_moon_applicable,
    next_new_moon_display,
)
from moonology_house_cosmic import HOUSE_COSMIC
from moonology_daily_narrative import (
    HOUSE_DAY_FEEL,
    PHASE_DAY_FEEL,
    SIGN_DAY_FEEL,
    build_daily_moon_reading,
)
from moonology_rules_data import MOON_PHASE_RULES

# Phases when Boland New / Full Moon ceremonies apply (NM up to 3 days per Ch.3)
NEW_MOON_APPLICABLE_PHASES = frozenset({"New Moon", "Waxing Crescent"})
FULL_MOON_APPLICABLE_PHASES = frozenset({"Full Moon"})

# Appendix / Ch.5 - house zones (full cosmic data in moonology_house_cosmic.py)
# 7th-house sign (whole-sign) from natal lagna - Ch.10 love FAQ table
LAGNA_TO_LOVE_SIGN: dict[str, str] = {
    "Aries": "Libra",
    "Taurus": "Scorpio",
    "Gemini": "Sagittarius",
    "Cancer": "Capricorn",
    "Leo": "Aquarius",
    "Virgo": "Pisces",
    "Libra": "Aries",
    "Scorpio": "Taurus",
    "Sagittarius": "Gemini",
    "Capricorn": "Cancer",
    "Aquarius": "Leo",
    "Pisces": "Virgo",
}

# Ch.3 - complete New Moon wish ritual (pp.42-44 OCR)
NEW_MOON_RITUAL_STEPS: list[str] = [
    "Feel gratitude: list 5-10 people or things you are grateful for; send them love.",
    "Play spiritual music; light a candle or incense; take deep cleansing breaths.",
    "Decide your Top 10 wishes/intentions for the coming four weeks plus actions to achieve them.",
    "Write, doodle, or draw all 10 wishes on paper (coloured pens add energy).",
    "Read each wish aloud; visualize it fulfilled; feel the joy in your body.",
    "Write an 'I am...' affirmation for each top wish.",
    "Score each wish 0-100 for believability; strengthen any below 50.",
    "Write one practical first step you intend to take for each wish.",
    "Meditate 15 minutes; release your dreams to the Universe.",
    "End with 'For the good of all or not at all!' and/or Om Namo Narayani (3x), "
    "or 'This or something better manifests for me, under grace in perfect ways.'",
    "Through the month act on wishes; at the next New Moon review results and thank the Universe.",
]

# Ch.6 - Full Moon forgiveness + gratitude ceremony (numbered)
FULL_MOON_RITUAL_STEPS: list[str] = [
    "On the night of the Full Moon, sit quietly 10+ minutes; mentally forgive all grudges.",
    "If someone upsets you, ask them to forgive your bad feelings; send them love.",
    "Deep cleansing breaths; release stress and worries.",
    "Write habits, upsets, and names of people to forgive - your forgiveness list.",
    "Visualize each person in a pink bubble, smiling; say 'I forgive you'; let them float away.",
    "Recite: Under the glorious Full Moon, I forgive everything and everyone; I forgive myself; "
    "love adjusts my life; I abide in peace.",
    "Optional: bring love to thoughts and relationships; call soul fragments to rejoin you.",
    "Safely burn the forgiveness list over a sink.",
    "Gratitude: name three blessings; feel them in your body; write and burn the gratitude list.",
    "Say: I know that I am blessed and I live my life within that knowing.",
]

# Ch.3 golden rules - rotate one per New Moon day
NEW_MOON_GOLDEN_TIPS: list[tuple[str, str]] = [
    ("Wish from the heart and feel it as already happened.", "rules44/Boland NM golden rules"),
    ("Think what you do want; do not dwell on what you lack.", "rules44/Boland NM golden rules"),
    ("Take baby steps toward big dreams across several lunations.", "rules44/Boland NM golden rules"),
    ("Wish for the feeling behind the thing, not envy of others.", "rules44/Boland NM golden rules"),
    ("Do not wish for a specific person to change - wish courage to leave if needed.", "rules44/Boland NM golden rules"),
    ("Ask: Am I worthy of what I am wishing for?", "rules44/Boland NM golden rules"),
    ("Be grateful for what you already have before wishing more.", "rules44/Boland NM golden rules"),
]

# Ch.2 / Ch.30 - phase-specific life tips
PHASE_SPECIAL_TIPS: dict[str, str] = {
    "New Moon": "Ideal window (up to 3 days) for written wishes; mantra: I am blessed.",
    "Waxing Crescent": "Re-read last wishes daily; 68 seconds of visualization strengthens them.",
    "First Quarter": "Double-commit or release wishes your heart has outgrown.",
    "Gibbous Moon": "Tweak plans; restart a good habit before fullness.",
    "Full Moon": "Best forgiveness work the night before exact Full Moon.",
    "Disseminating Moon": "Share one lesson learned; rest before the next build phase.",
    "Third Quarter": "Break one bad habit; choose what to carry into the next cycle.",
    "Balsamic Moon": "Chant Om Namo Narayani; cut hair/nails now if you want slower regrowth.",
}

# Ch.1 - Moon governs (daily mood context)
MOON_GOVERNS: str = (
    "Emotions, food, home, instincts, nurturing, habits, moods, and the subconscious - "
    "the Moon is your cosmic timer for when to act, rest, wish, or release."
)


def _seed(target: date, moon_sign: str, house: int, phase: str) -> int:
    return (
        target.toordinal() * 17
        + sum(ord(c) for c in moon_sign)
        + house * 13
        + sum(ord(c) for c in phase)
    )


def _apply_phase_display(
    out: dict[str, Any],
    *,
    target: date,
    timezone: float,
    place: str,
) -> None:
    """Before exact New Moon, show Balsamic guidance — not wish-ritual New Moon copy."""
    phase = out.get("phase", "")
    if phase not in ("New Moon", "Waxing Crescent"):
        return
    if is_new_moon_applicable(target, timezone):
        return
    rules = MOON_PHASE_RULES.get("Balsamic Moon", {})
    out["phase_astronomical"] = phase
    out["phase"] = "Balsamic Moon"
    out["phase_keywords"] = rules.get("keywords", "")
    out["phase_summary"] = rules.get("summary", "")
    out["phase_remedy"] = rules.get("remedy", "")
    out["phase_dos"] = [
        {"text": t, "source": s} for t, s in rules.get("dos", [])[:2]
    ]
    out["phase_donts"] = [
        {"text": t, "source": s} for t, s in rules.get("donts", [])[:1]
    ]
    nxt = next_new_moon_display(target, timezone)
    loc = f" ({place})" if place else ""
    out["phase_note"] = (
        f"Moon is nearly dark ({phase} in the sky). New Moon wishing starts after "
        f"{nxt}{loc} — rest and prep today, ritual tomorrow."
    )


def apply_moonology_extras(
    base: dict[str, Any],
    *,
    target: date,
    client: str = "You",
    natal_sun_sign: str,
    natal_lagna: str,
    timezone: float = 5.5,
    place: str = "",
) -> dict[str, Any]:
    """Merge book-backed lunation, house cosmic extras, and life-improvement picks."""
    out = dict(base)
    moon_sign = out.get("moon_sign", "")

    is_new_moon_day = is_new_moon_applicable(target, timezone)
    is_full_moon_day = is_full_moon_applicable(target, timezone)
    _apply_phase_display(out, target=target, timezone=timezone, place=place)

    phase = out.get("phase", "")
    house = int(out.get("house_from_asc", 1))
    seed = _seed(target, moon_sign, house, phase)

    cosmic = HOUSE_COSMIC.get(house, {})
    out["house_zone"] = cosmic.get("zone", "")
    out["house_focus"] = cosmic.get("focus", "")
    out["house_mantra"] = cosmic.get("mantra", "")
    out["house_chakra"] = cosmic.get("chakra", "")
    out["house_oil"] = cosmic.get("oil", "")
    out["house_oil_use"] = cosmic.get("oil_use", "")
    out["house_archangel"] = cosmic.get("archangel", "")
    out["house_archangel_note"] = cosmic.get("archangel_note", "")
    out["house_goddess"] = cosmic.get("goddess", "")
    out["house_goddess_note"] = cosmic.get("goddess_note", "")
    out["house_ritual"] = cosmic.get("house_ritual", "")
    out["house_affirmations"] = cosmic.get("affirmations", [])
    out["moon_governs"] = MOON_GOVERNS

    out["lunation_applicable"] = "new_moon" if is_new_moon_day else ("full_moon" if is_full_moon_day else "")
    out["lunation_window_note"] = ""
    timing: dict[str, Any] | None = None
    if is_new_moon_day:
        timing = compute_lunation_timing(target, kind="new_moon", timezone=timezone, place=place)
        out["lunation_timing"] = timing
        if timing:
            out["lunation_window_note"] = (
                f"Exact New Moon: {timing['exact_display']} ({timing['timezone_label']}"
                f"{', ' + place if place else ''}). "
                f"Best ritual window: {timing['peak_window_start_display']} to "
                f"{timing['peak_window_end_display']}. "
                f"Extended window ends: {timing['extended_window_end_display']}."
            )
        else:
            out["lunation_window_note"] = (
                "New Moon window active (ideally within 8 hours of exact New Moon; "
                "up to 3 days is fine per Boland Ch.3). Do the wish ritual today."
            )
    elif is_full_moon_day:
        timing = compute_lunation_timing(target, kind="full_moon", timezone=timezone, place=place)
        out["lunation_timing"] = timing
        if timing:
            out["lunation_window_note"] = (
                f"Exact Full Moon: {timing['exact_display']} ({timing['timezone_label']}"
                f"{', ' + place if place else ''}). "
                f"Ceremony night: {timing['ceremony_start_display']} to "
                f"{timing['ceremony_end_display']}. "
                f"Also good: {timing['alt_ceremony_start_display']} to "
                f"{timing['alt_ceremony_end_display']} (night before)."
            )
        else:
            out["lunation_window_note"] = (
                "Full Moon day - perform forgiveness and gratitude ceremony tonight "
                "(night before is also powerful per Ch.6)."
            )

    love_sign = LAGNA_TO_LOVE_SIGN.get(natal_lagna, "")
    out["love_zone_sign"] = love_sign
    if moon_sign == love_sign:
        out["love_zone_note"] = (
            f"Moon in your Love Zone sign ({love_sign}) - feelings about partnerships "
            "may surface; good day for romance or honest couple talk."
        )
    elif house == 7:
        out["love_zone_note"] = (
            "Daily Moon crosses your 7th House (Love Zone) - one-on-one relating is highlighted."
        )

    if natal_sun_sign and moon_sign == natal_sun_sign:
        out["personal_lunation"] = (
            f"Personal New Moon window: transit Moon meets your natal Sun in {natal_sun_sign} - "
            "renewal and emotional hot spot; ideal for self-focused wishes."
        )

    nm_focus = NEW_MOON_IN_SIGN.get(moon_sign, [])
    fm_data = FULL_MOON_IN_SIGN.get(moon_sign, {})
    phase_tip = PHASE_SPECIAL_TIPS.get(phase, "")
    if phase == "New Moon" and not is_new_moon_day:
        phase_tip = PHASE_SPECIAL_TIPS.get("Balsamic Moon", phase_tip)

    extras_dos: list[dict] = []
    ritual: list[str] = []

    if is_new_moon_day:
        picks = list(nm_focus) if nm_focus else []
        out["lunation_title"] = f"New Moon in {moon_sign} - DO TODAY"
        out["lunation_focus"] = picks
        ritual = list(NEW_MOON_RITUAL_STEPS)
        tip = NEW_MOON_GOLDEN_TIPS[seed % len(NEW_MOON_GOLDEN_TIPS)]
        out["golden_tip"] = {"text": tip[0], "source": tip[1]}
        out["life_improvement"] = picks[0] if picks else phase_tip
        if cosmic.get("house_ritual"):
            picks.append(f"House ritual: {cosmic['house_ritual']}")
        if cosmic.get("affirmations"):
            picks.append(f"Affirm today: {cosmic['affirmations'][seed % len(cosmic['affirmations'])]}")
        out["things_to_do"] = picks
    elif is_full_moon_day:
        qs = fm_data.get("questions", [])
        q = qs[seed % len(qs)] if qs else ""
        out["lunation_title"] = f"Full Moon in {moon_sign} - DO TONIGHT"
        out["lunation_energy"] = fm_data.get("energy", "")
        out["lunation_message"] = fm_data.get("message", "")
        out["lunation_balance"] = fm_data.get("balance", "")
        out["reflection_question"] = q
        out["things_to_do"] = [
            "Perform Full Moon forgiveness ceremony (write list, pink bubbles, burn safely).",
            "Gratitude ceremony - three blessings, write and burn list.",
            f"Reflect: {q}" if q else "",
            "Perform forgiveness ceremony per Ch.6.",
        ]
        out["things_to_do"] = [t for t in out["things_to_do"] if t]
        ritual = list(FULL_MOON_RITUAL_STEPS)
        out["life_improvement"] = fm_data.get("message", phase_tip)
    elif phase in ("First Quarter", "Gibbous Moon"):
        out["lunation_title"] = f"Building toward Full Moon ({moon_sign})"
        if nm_focus:
            out["lunation_focus"] = [nm_focus[(seed + 2) % len(nm_focus)]]
        out["life_improvement"] = phase_tip
    elif phase in ("Disseminating Moon", "Third Quarter", "Balsamic Moon"):
        qs = fm_data.get("questions", [])
        if qs:
            out["reflection_question"] = qs[(seed + 1) % len(qs)]
        out["lunation_title"] = f"Waning cycle ({moon_sign})"
        out["life_improvement"] = phase_tip
        if phase == "Balsamic Moon":
            ritual = [
                "Chant Om Namo Narayani three times - I surrender to the Divine.",
                "Rest, daydream, and gently preview next month's wishes.",
                "Optional: cut hair/nails if you want slower regrowth (Boland p.30).",
            ]
    else:
        out["life_improvement"] = phase_tip

    out["phase_special_tip"] = phase_tip
    out["ritual_steps"] = ritual
    if cosmic.get("mantra"):
        extras_dos.append({
            "text": f"Chant {cosmic['mantra']} today to balance {cosmic.get('chakra', 'chakra')} "
                    f"while Moon is in your {_ordinal(house)} House ({cosmic.get('zone', '')}).",
            "source": "rules44/Boland Appendix C house mantra",
        })
    out["moonology_extras"] = extras_dos

    reading = build_daily_moon_reading(
        client=client,
        target=target,
        moon_sign=moon_sign,
        moon_house=house,
        lagna=natal_lagna,
        phase=phase,
        phase_astronomical=out.get("phase_astronomical", ""),
        phase_note=out.get("phase_note", ""),
        element=out.get("element", ""),
        lunation_applicable=out.get("lunation_applicable", ""),
        lunation_timing=out.get("lunation_timing"),
        love_zone_note=out.get("love_zone_note", ""),
        personal_lunation=out.get("personal_lunation", ""),
        is_new_moon_day=is_new_moon_day,
        is_full_moon_day=is_full_moon_day,
        new_moon_themes=nm_focus if is_new_moon_day else None,
        full_moon_message=fm_data.get("message", "") if is_full_moon_day else "",
    )
    out.update(reading)
    if reading.get("daily_reading"):
        out["life_improvement"] = reading["practical_paragraph"] or out.get("life_improvement", "")
    if moon_sign in SIGN_DAY_FEEL:
        out["sign_summary"] = f"You may notice that {SIGN_DAY_FEEL[moon_sign]}."
    if house in HOUSE_DAY_FEEL:
        out["house_summary"] = f"In your chart today, {HOUSE_DAY_FEEL[house]}."
    if phase in PHASE_DAY_FEEL:
        out["phase_summary"] = PHASE_DAY_FEEL[phase].capitalize() + "."

    return out


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"
