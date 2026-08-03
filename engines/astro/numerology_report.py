#!/usr/bin/env python3
"""Deterministic numerology report generator — no LLM.

Reproduces the gold client format
``reports/Ritz_reprot/Numerology_Ritz_19850308.html`` purely from name + DOB,
applying the documented rules in ``numerology_skill.md`` (Woods / rules23 +
Avasthi / rules38). Every number, cycle and date is computed; the interpretive
prose comes from fixed, book-faithful lookup tables (same approach as palm_api).

Usage:
    python3 numerology_report.py --name "Ritz" --dob 1985-03-08 \
        --sex Male --report-date 2026-04-08 --out reports/Numerology_Ritz_1985-03-08.html
"""
from __future__ import annotations

import argparse
import itertools
import re
from datetime import date, timedelta
from collections import Counter
from html import escape

# ───────────────────────── ciphers ─────────────────────────
# Chaldean (no 9) — used for name harmony / correction (Avasthi).
_CHALDEAN_GROUPS = {
    1: "AIJQY", 2: "BKR", 3: "CGLS", 4: "DMT",
    5: "EHNX", 6: "UVW", 7: "OZ", 8: "FP",
}
CHALDEAN = {ch: val for val, letters in _CHALDEAN_GROUPS.items() for ch in letters}

# Pythagorean (A=1..I=9, J=1..R=9, S=1..Z=8) — soul portrait (Woods).
PYTHAG = {chr(ord("A") + i): (i % 9) + 1 for i in range(26)}

VOWELS = set("AEIOU")
PLANET = {1: "Sun", 2: "Moon", 3: "Jupiter", 4: "Rahu", 5: "Mercury",
          6: "Venus", 7: "Ketu", 8: "Saturn", 9: "Mars"}
# Weekday → numerology lord (Python weekday: Mon=0 … Sun=6).
WEEKDAY_LORD = {0: 2, 1: 9, 2: 5, 3: 3, 4: 6, 5: 8, 6: 1}
WEEKDAY_ABBR = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
MASTERS = (11, 22, 33)


def reduce_num(n: int, keep_master: bool = True) -> int:
    while n > 9 and not (keep_master and n in MASTERS):
        n = sum(int(d) for d in str(n))
    return n


def planet_label(n: int) -> str:
    if n in PLANET:
        return f"{n} ({PLANET[n]})"
    if n in MASTERS:
        root = reduce_num(n, keep_master=False)
        return f"{n} (Master → {root} / {PLANET[root]})"
    return str(n)


def planet_name(n: int) -> str:
    if n in PLANET:
        return PLANET[n]
    if n in MASTERS:
        return PLANET[reduce_num(n, keep_master=False)]
    return str(n)


def letter_values(name: str, cipher: dict) -> list[tuple[str, int]]:
    return [(c.upper(), cipher[c.upper()]) for c in name if c.upper() in cipher]


def name_total(name: str, cipher: dict, only=None) -> int:
    total = 0
    for c in name:
        u = c.upper()
        if u not in cipher:
            continue
        if only == "vowel" and u not in VOWELS:
            continue
        if only == "consonant" and u in VOWELS:
            continue
        total += cipher[u]
    return total


# ───────────────────────── interpretation tables ─────────────────────────
KARMIC_DEBTS = {13, 14, 16, 19}
KARMIC_DEBT_TEXT = {
    13: "Debt of work avoided in the past — shortcuts backfire; the work itself is the only real answer.",
    14: "Debt of misused freedom — balance liberty with responsibility, especially in money and romance.",
    16: "Debt of ego in relationships — pride and broken bonds; humility and honest love reset it.",
    19: "Debt of over-self-reliance — learn to receive help so independence does not harden into isolation.",
}

# Maha (45-year chapter) — short labels; full prose from DASHA_PREDICT (Avasthi OCR).
MAHA_THEME = {
    1: "leadership tests, visibility and ego clarity — step into the light, own decisions.",
    2: "mood-led cycles, partnerships and public feeling; home or mother themes come forward.",
    3: "growth, teaching, optimism and mentors — strong for study and long-view plans.",
    4: "twists, ambition spikes and unconventional paths; strong for IT, media, or work abroad.",
    5: "business, documents, speech, travel and trade — the busiest, most multi-tasking stretch; cash flow and networking.",
    6: "comfort, marriage focus, deals and harmony; also indulgence — watch contracts and health habits.",
    7: "inward turn, letting go, research or spirituality; odd luck; partnerships need space and honesty.",
    8: "discipline, duty, authority and a slow climb; rewards from past effort — or debts from past shortcuts.",
    9: "push, competition, courage and quick moves; risk of clashes — channel energy into sport, study, or career sprints.",
}

# Avasthi Ank Jyotish OCR — Dasha Results (pp.200–240+). Grid-aware: absent / present / double.
DASHA_PREDICT: dict[int, dict[str, str]] = {
    1: {
        "core": "Sun energy — visibility, authority, and the need to be respected.",
        "absent": "With 1 open in the chart, confidence and leadership surge; ego and temper can rise — use it for fair command, not fights.",
        "present": "With 1 already placed, the book notes a softer Sun year: less anger, steadier confidence.",
        "antar": "A Sun birthday-year favours recognition, bosses, and putting your name on the work.",
        "praty": "Good for one bold step with seniors — a pitch, interview, or public decision.",
    },
    2: {
        "core": "Moon energy — feelings, family, and public mood lead the story.",
        "absent": "With 2 open, emotions run closer to the surface; networking and tact work well; guard rest and mother/home themes.",
        "present": "With 2 already in the chart, the Moon year deepens sensitivity — partnerships need extra patience.",
        "antar": "A Moon year favours family moves, emotional honesty, and teamwork.",
        "praty": "Prioritise rest, trusted talks, and home matters over drama.",
    },
    3: {
        "core": "Jupiter energy — learning, teachers, optimism, and growth.",
        "absent": "With 3 open, study, counsel, and spiritual curiosity strengthen; seek good advice before big bets.",
        "present": "With 3 already placed, Jupiter's year is less about new starts — more about using wisdom you already have.",
        "antar": "A Jupiter year suits courses, legal clarity, teaching, and long-view plans.",
        "praty": "Sign contracts, finish study modules, or ask a mentor one clear question.",
    },
    4: {
        "core": "Rahu energy — ambition, media, foreign links, and unconventional moves.",
        "absent": "With 4 open, the book warns of mood swings, illusion, and accident/debt risk — verify facts before you leap.",
        "present": "With 4 in the chart, Rahu's edge turns sharper — bold moves can work if paperwork is clean.",
        "double": "Double 4 intensifies Rahu — compulsive risks; only act on checked plans.",
        "antar": "A Rahu year pushes bigger networks and reputation plays — stay ethical and documented.",
        "praty": "Launch one calculated risk; skip gossip and shortcut schemes.",
    },
    5: {
        "core": "Mercury energy — speech, trade, travel, and quick thinking.",
        "absent": "With 5 open, money and communication improve; sharp deals, writing, and routine work pay.",
        "present": "With 5 placed, mind races faster — great for business, but watch overthinking.",
        "double": "Double 5 adds money flow with mental strain — pace yourself.",
        "antar": "A Mercury year favours papers, talks, sales, and short travel.",
        "praty": "Best window for email, study, signing, and negotiation.",
    },
    6: {
        "core": "Venus energy — comfort, love, beauty, and fair agreements.",
        "absent": "With 6 open, relationships, home pleasure, and aesthetics matter more — invest in harmony deliberately.",
        "present": "With 6 placed, Venus can turn quarrelsome — watch harsh words and luxury overspend.",
        "double": "Double 6 warns of ego in love and money spent to impress.",
        "antar": "A Venus year favours marriage talks, design, art, and peaceful settlements.",
        "praty": "Repair a bond, beautify home, or close a fair deal.",
    },
    7: {
        "core": "Ketu energy — research, spirituality, letting go, and inner luck.",
        "absent": "With 7 open, the book promises easier wishes, travel, and spiritual depth — struggles ease if you stay honest.",
        "present": "With 7 placed (as your Destiny is), Ketu brings change and restlessness — adapt rather than resist.",
        "double": "Double 7 amplifies upheaval — expect relocations or role shifts.",
        "antar": "A Ketu year favours research, trimming clutter, and quiet wins over loud fame.",
        "praty": "Low drama; research, health routine, or spiritual practice.",
    },
    8: {
        "core": "Saturn energy — duty, delay, discipline, and long-term results.",
        "absent": "With 8 open, hard work is mandatory; delays and budget pressure test patience — persist without bitterness.",
        "present": "With 8 in the chart (your birth-day), Saturn rewards grind — titles, property, and legacy build slowly but surely.",
        "double": "Double 8 doubles duty — avoid shortcuts; structure is your friend.",
        "antar": "A Saturn year favours senior approvals, savings, and career walls built brick by brick.",
        "praty": "Persist with bureaucracy; do not force fast yes-es.",
    },
    9: {
        "core": "Mars energy — courage, competition, property, and decisive action.",
        "absent": "With 9 open, drive and completion rise — sport, sales pushes, and brave finishes work.",
        "present": "With 9 placed, Mars runs hotter — channel energy professionally, not into domestic war.",
        "double": "Double 9 warns of clashes — compete with rules.",
        "antar": "A Mars year favours bold projects, travel, and athletic effort.",
        "praty": "Push one goal; watch temper and fatigue.",
    },
}
LIFE_PATH = {
    1: ("the leader's number", "independent, pioneering, self-starting; born to initiate and lead, learning not to dominate."),
    2: ("the diplomat's number", "sensitive, cooperative, peace-making; gifted in partnership and intuition, learning to value your own needs."),
    3: ("the communicator's number", "expressive, creative, social and optimistic; gifted with words and art, learning focus over scatter."),
    4: ("the builder's number", "disciplined, practical, methodical; you create lasting structure through patient work."),
    5: ("the adventurer's number", "versatile, freedom-loving, quick — travel, change and communication; learning constructive focus."),
    6: ("the carer's number", "responsible, nurturing, home- and beauty-oriented; service to family and community, learning healthy boundaries."),
    7: ("the analyst's number", "research, technical depth, advisory, investigation and teaching; expertise over showmanship, with travel and restlessness in the lane."),
    8: ("the executive's number", "ambition, authority, money and management; material mastery built through effort and time."),
    9: ("the humanitarian's number", "compassionate, idealistic, completion-minded; you do best when the win helps something larger than ego."),
    11: ("a master number", "high intuition, inspiration and spiritual sensitivity; a teacher/illuminator, learning to ground the vision."),
    22: ("the master builder", "large-scale practical vision — building things that serve many; learning to handle the pressure of the gift."),
    33: ("the master teacher", "selfless service and healing through love; a rare nurturing-teacher vibration."),
}
EXPRESSION = {
    1: "visible initiative — starting things, heading projects, putting your name on the work; remembered as the one who stepped forward.",
    2: "partnership and tact — building through cooperation, sensitivity and behind-the-scenes glue.",
    3: "creative expression — words, art, performance and social warmth; you inspire and entertain.",
    4: "reliable construction — systems, order and dependable delivery; the one who makes it actually work.",
    5: "versatile communication — selling, connecting, travelling, adapting; thrives on variety.",
    6: "responsibility and care — counsel, beauty, family and community; the dependable harmoniser.",
    7: "analysis and depth — research, specialism and quiet mastery; the expert and investigator.",
    8: "executive power — organising money, people and enterprise toward tangible results.",
    9: "humanitarian breadth — leading causes, teaching and completing; a wide, generous reach.",
    11: "inspired influence — uplifting others through intuition and vision.",
    22: "master-builder destiny — turning big ideals into concrete institutions.",
    33: "healing teacher — service to many through compassion.",
}
SOUL_URGE = {
    1: "to lead and stand independent — your heart wants achievement on your own terms.",
    2: "for harmony, love and partnership — your heart wants peace and to be needed.",
    3: "for joyful self-expression — your heart wants to create, speak and be seen.",
    4: "for order and security — your heart wants something solid that lasts.",
    5: "for freedom and experience — your heart wants variety, travel and the new.",
    6: "to nurture and beautify — your heart wants home, family and to be of service.",
    7: "for truth and understanding — your heart wants depth, study and quiet.",
    8: "for mastery and abundance — your heart wants influence and material success well used.",
    9: "for meaning, completion and bigger-picture justice — your heart wants to help something larger than ego.",
    11: "for spiritual inspiration — your heart wants to illuminate and uplift.",
    22: "to build something of lasting collective value.",
    33: "to heal and teach through unconditional care.",
}
PERSONALITY = {
    1: "confident, self-directed, ready to lead — people may read you as more absolute than you feel inside.",
    2: "gentle, approachable, diplomatic — you put others at ease.",
    3: "charming, expressive, fun — you come across creative and sociable.",
    4: "solid, sincere, dependable — you look like someone who can be trusted with the work.",
    5: "lively, magnetic, curious — you read as adaptable and quick.",
    6: "warm, responsible, caring — you give the impression of a protector and host.",
    7: "reserved, thoughtful, dignified — you can seem private or aloof until known.",
    8: "authoritative, capable, success-minded — you project competence and control.",
    9: "gracious, worldly, idealistic — you appear compassionate and broad-minded.",
    11: "inspiring and intense — a sensitive, magnetic first impression.",
    22: "calm, capable and quietly ambitious on a large scale.",
    33: "warm, wise and selfless in presence.",
}
# Missing Lo Shu digit → (planet, lifestyle habit, health note).
MISSING_DIGIT = {
    1: ("Sun", "claim leadership moments and personal pride on purpose; speak up early.", "heart and general vitality"),
    2: ("Moon", "book rest and emotional check-ins on the calendar — they will not run on autopilot.", "fluids, sleep and emotional balance"),
    3: ("Jupiter", "create on purpose — write, speak, learn; cultivate optimism and good counsel.", "liver and weight regulation"),
    4: ("Rahu", "when you want change, take one calculated risk with paperwork clear — avoid chaos for its own sake.", "nervous system and immunity"),
    5: ("Mercury", "build communication and adaptability deliberately; learn, network, travel.", "nerves, speech and digestion"),
    6: ("Venus", "deliberately invest in comfort, aesthetics, affection and fair deals; choose the peaceful win.", "kidneys, throat and reproductive comfort"),
    7: ("Ketu", "keep a weekly study or silence block — even 20 minutes; trust the hunches, verify the facts.", "immunity and stress fatigue"),
    8: ("Saturn", "build discipline, savings and long-term structures consciously; respect time.", "bones, joints and teeth"),
    9: ("Mars", "channel courage and drive into sport or a cause; finish what you start.", "blood, energy and inflammation"),
}
# Avasthi Book of Remedies (rules41) — planet support for open grid digits; NOT numerology-specific objects.
PLANET_REMEDY = {
    1: {"color": "red or orange on Sundays", "behavior": "respect father and authority; brief sun-facing routine at sunrise",
        "charity": "wheat and jaggery on Sundays", "gem": "Ruby (Garnet alternative) in gold/copper, ring finger, Sunday"},
    2: {"color": "white on Mondays", "behavior": "respect mother; steady water intake; wear clean white clothes",
        "charity": "rice, milk or silver on Mondays", "gem": "Pearl (Moonstone alternative) in silver, Monday"},
    3: {"color": "yellow on Thursdays", "behavior": "respect teachers; keep learning visible in the calendar",
        "charity": "yellow clothes and chana dal to a teacher or priest on Thursdays",
        "gem": "Yellow Sapphire (Sunela/Amber alternative) in gold, index finger, Thursday"},
    4: {"color": "avoid excessive black/blue if Rahu feels chaotic", "behavior": "channel ambition through one verified plan at a time",
        "charity": "udad dal on Wednesday or Saturday", "gem": "Gomed (Black Onyx alternative) in silver, Saturday"},
    5: {"color": "green on Wednesdays", "behavior": "gardening, writing, networking; keep speech clear and honest",
        "charity": "books or moong dal on Wednesdays", "gem": "Emerald (Green Onyx alternative) in gold, Wednesday"},
    6: {"color": "white or decorative clothes on Fridays", "behavior": "respect partner; grooming; fair deals at home",
        "charity": "ghee to temple or gaushala on Fridays", "gem": "Diamond (Fire Opal/White Opal alternative) in silver, Friday"},
    7: {"color": "grey or two-tone neutrals on Tuesdays", "behavior": "weekly quiet study; worship Ganesha; avoid smoky foods",
        "charity": "blankets to the poor on Tuesdays", "gem": "Cat's Eye (Turquoise/Agate alternative), Tuesday/Wednesday"},
    8: {"color": "black or blue on Saturdays", "behavior": "discipline, humility toward workers; avoid alcohol excess",
        "charity": "udad dal, mustard oil or iron items on Saturdays",
        "gem": "Blue Sapphire — test 3 days first (Amethyst alternative), Saturday"},
    9: {"color": "red on Tuesdays", "behavior": "channel anger into sport or service; protect siblings' dignity",
        "charity": "red masoor dal or blood donation on Tuesdays", "gem": "Red Coral (Red Hakik alternative) in copper, Tuesday"},
}
# Woods (rules23) — karmic lessons = digits missing from the birth NAME, not the grid.
KARMIC_LESSON_WOODS = {
    1: "develop initiative and self-confidence; stop waiting for others to lead.",
    2: "cultivate patience, tact and teamwork without needing praise.",
    3: "release harsh self-criticism; express yourself without waiting for perfection.",
    4: "build self-discipline and an inner compass — stop chasing every new shortcut.",
    5: "welcome change and flexibility; loosen rigid routines.",
    6: "open up in relationships; take responsibility for home and affection honestly.",
    7: "go deeper — study and spiritual practice need steady effort, not surface skimming.",
    8: "balance ambition with financial discipline; avoid reckless risk.",
    9: "broaden empathy; give time to others' wellbeing, not only your own goals.",
}
STRONG_CELL = {
    1: "leadership moments and pride when you choose to step up.",
    2: "emotional intelligence, partnership and public feeling.",
    3: "judgment, teaching and creative communication.",
    4: "method, persistence and the ability to make systems work.",
    5: "a quick mind, commerce and speech.",
    6: "care, beauty and responsibility for others.",
    7: "research depth, intuition and specialism.",
    8: "stamina, duty, work ethic and late reward — built for long projects.",
    9: "drive, courage and the will to complete.",
}
LUCKY_SERIES = {d: [d + 9 * k for k in range(11)] for d in range(1, 10)}
AVASTHI_GROUPS = {"A": [1, 4, 8], "B": [3, 6, 9], "C": [2, 5, 7]}
AVASTHI_THEME = {
    "A": "Ambition, discipline, material achievement (Sun–Rahu–Saturn)",
    "B": "Creativity, love, spirituality (Jupiter–Venus–Mars)",
    "C": "Sensitivity, intellect, introspection (Moon–Mercury–Ketu)",
}


def avasthi_group(n: int) -> str:
    for g, nums in AVASTHI_GROUPS.items():
        if reduce_num(n, keep_master=False) in nums:
            return g
    return "A"


def _root(n: int) -> int:
    return reduce_num(n, keep_master=False)


def _valid_compound(total: int) -> bool:
    return total > 0 and total not in KARMIC_DEBTS


# Woods — balance number coping (initials only, Pythagorean, masters reduced).
BALANCE_TEXT = {
    1: "draw strength from within but talk problems through with people you trust — isolation makes challenges harder.",
    2: "lean on tact and diplomacy; trust your voice to diffuse tension rather than avoiding confrontation.",
    3: "stay lighthearted; use creativity for unexpected fixes and let small irritations roll off.",
    4: "use self-discipline to control anger; step back for the bigger picture and aim for fairness.",
    5: "face setbacks head-on; avoid escapism and use your wide perspective for a creative fix.",
    6: "own the fix yourself — nurture others often, but you must also take responsibility for your own problems.",
    7: "use your sharp mind to dissect the issue, but do not hide in your inner world so long that action stalls.",
    8: "solve your own problems directly; resist manipulating others when power feels like the quickest exit.",
    9: "lift your view to the bigger picture; empathy is your steadiness tool — do not retreat from people entirely.",
}


def _missing_remedy_lines(open_digits: list[int]) -> str:
    """Book-backed open-digit support: habit + rules41 color/charity/behavior; gem optional."""
    if not open_digits:
        return ""
    lines = []
    for n in open_digits:
        planet, habit, _ = MISSING_DIGIT[n]
        pr = PLANET_REMEDY[n]
        lines.append(
            f"<li><strong>Open {n} ({planet}):</strong> {escape(habit)} "
            f"<span class=\"fine\">Colour: {escape(pr['color'])}. "
            f"Behaviour: {escape(pr['behavior'])}. "
            f"Charity: {escape(pr['charity'])}. "
            f"Optional gem (rules41): {escape(pr['gem'])}.</span></li>"
        )
    return "".join(lines)


def _period_remedy_line(pos: dict) -> str:
    """Current Mahā/Antar lord — rules41 priority."""
    mc, ant = pos["maha"], pos["antar_n"]
    pr_m = PLANET_REMEDY.get(mc["num"], {})
    pr_a = PLANET_REMEDY.get(ant, {})
    return (
        f"<p class=\"pred\"><strong>Active period support:</strong> "
        f"Mahā <strong>{mc['planet']}</strong> — {escape(pr_m.get('behavior', 'align effort with the chapter theme.'))} "
        f"Antar <strong>{PLANET[ant]}</strong> this year — {escape(pr_a.get('color', 'use the planet colour on its weekday.'))}</p>"
    )


def _effective_loshu_counts(c: dict) -> Counter:
    """Lo Shu tally with Basic + Destiny placed (display grid)."""
    counts = Counter(c["loshu"])
    counts[_root(c["birth_day"])] += 1
    counts[_root(c["life_path"])] += 1
    return counts


def _strong_digits_text(c: dict) -> str:
    top = [n for n, _ in c["loshu"].most_common(3) if c["loshu"][n] >= 2]
    if not top:
        top = [n for n, cnt in c["loshu"].most_common(2) if cnt]
    if not top:
        return ""
    bits = [f"<strong>{n}</strong> — {STRONG_CELL.get(n, 'repeated birth-date strength.')}" for n in top]
    return "<p class=\"pred\"><strong>Strongest birth-date repeats:</strong> " + "; ".join(bits) + "</p>"


def _digit_grid_status(n: int, c: dict) -> str:
    """How digit n sits in birth chart (Lo Shu + Basic/Destiny placed)."""
    cnt = c["loshu"].get(n, 0)
    if n == _root(c["birth_day"]) or n == _root(c["life_path"]):
        cnt = max(cnt, 1)
    if cnt >= 2:
        return "double"
    if cnt >= 1:
        return "present"
    return "absent"


def _pillar_match_note(n: int, c: dict) -> str:
    if n == _root(c["birth_day"]):
        return " This is your birth-day number — Avasthi says core identity and purpose feel louder now."
    if n == _root(c["life_path"]):
        return " This is your Destiny number — a turning-point chapter for life-path events."
    return ""


def _dasha_prediction(n: int, c: dict, layer: str = "maha") -> str:
    """Human dasha line from Avasthi OCR; layer = maha | antar | praty."""
    d = DASHA_PREDICT[n]
    if layer == "praty":
        return d.get("praty", d["core"])
    if layer == "antar":
        return d.get("antar", d["core"]) + _pillar_match_note(n, c)
    status = _digit_grid_status(n, c)
    text = d["core"]
    mod = d.get(status) or d.get("absent" if status == "absent" else "present", "")
    if mod:
        text = f"{text} {mod}"
    return text + _pillar_match_note(n, c)


def _timing_narrative(c: dict, pos: dict) -> str:
    """Plain-English Mahā + Antar + Pratyantar (Avasthi hierarchy analogy, p.189)."""
    mc = pos["maha"]
    ant = pos["antar_n"]
    pr = pos["praty_cur"]
    bday_y = pos["antar_year"]
    return (
        f"Your timing works in three nested layers. The <strong>major chapter</strong> "
        f"(Avasthi: like the prime minister) is <strong>{mc['planet']}</strong> "
        f"until {mc['end']}: {_dasha_prediction(mc['num'], c, 'maha')}"
        f"<br><br>The <strong>birthday year</strong> (chief minister) is "
        f"<strong>{PLANET[ant]}</strong> for the year starting your {bday_y} birthday: "
        f"{_dasha_prediction(ant, c, 'antar')}"
        f"<br><br>The <strong>active slice right now</strong> (mayor / local timing) is "
        f"<strong>{pr['planet']}</strong> until {fmt_short(pr['end'])} {pr['end'].year}: "
        f"{_dasha_prediction(pr['num'], c, 'praty')}"
    )


def _effective_grid_missing(c: dict) -> tuple[list[int], list[int], set[int]]:
    """Lo Shu tally + Avasthi Basic & Destiny placed in grid (OCR p.72).

    Returns (effective_missing, raw_date_missing, pillar_only_digits).
    """
    present = {n for n in range(1, 10) if c["loshu"].get(n, 0) > 0}
    raw_missing = [n for n in range(1, 10) if n not in present]
    bd_r = _root(c["birth_day"])
    lp_r = _root(c["life_path"])
    pillar_only: set[int] = set()
    for pillar in (bd_r, lp_r):
        if pillar not in present:
            pillar_only.add(pillar)
        present.add(pillar)
    effective = [n for n in range(1, 10) if n not in present]
    return effective, raw_missing, pillar_only


def _ank_grid_missing(c: dict) -> list[int]:
    """Vedic Ank Kundli (no century) + Basic + Destiny in permanent cells."""
    present = {n for n in range(1, 10) if c["ank"].get(n, 0) > 0}
    present.add(_root(c["birth_day"]))
    present.add(_root(c["life_path"]))
    return [n for n in range(1, 10) if n not in present]


def _harmony_targets(bd: int, lp: int) -> list[tuple[int, str, int]]:
    """Preferred Chaldean roots: (root, reason, priority 0=best)."""
    bd_r, lp_r = _root(bd), _root(lp)
    out: list[tuple[int, str, int]] = []
    seen: set[int] = set()

    def add(root: int, reason: str, pri: int) -> None:
        if root not in seen:
            out.append((root, reason, pri))
            seen.add(root)

    add(bd_r, f"match Basic (birth-day) {_root_label(bd)}", 0)
    add(lp_r, f"match Destiny (Life Path) {_root_label(lp)}", 1)
    g_bd, g_lp = avasthi_group(bd_r), avasthi_group(lp_r)
    for n in AVASTHI_GROUPS[g_bd]:
        add(n, f"harmonise with Basic group {g_bd} ({', '.join(map(str, AVASTHI_GROUPS[g_bd]))})", 2)
    if g_lp != g_bd:
        for n in AVASTHI_GROUPS[g_lp]:
            add(n, f"harmonise with Destiny group {g_lp} ({', '.join(map(str, AVASTHI_GROUPS[g_lp]))})", 3)
    return sorted(out, key=lambda x: x[2])


def _root_label(n: int) -> str:
    if n in MASTERS:
        return f"{n} (master → {_root(n)})"
    return str(n)


def assess_name_harmony(c: dict) -> dict:
    """Discordance flags + narrative inputs (Avasthi pp. 62–63, numerology_skill.md)."""
    bd, lp = c["birth_day"], c["life_path"]
    bd_r, lp_r = _root(bd), _root(lp)
    ch_r, ch_tot = c["chaldean_root"], c["chaldean_total"]
    expr_r = _root(c["expression"])
    g_bd, g_lp, g_ch, g_ex = (avasthi_group(x) for x in (bd_r, lp_r, ch_r, expr_r))

    gap_lp = abs(ch_r - lp_r)
    gap_bd = abs(ch_r - bd_r)
    same_grp_bd = g_ch == g_bd
    same_grp_lp = g_ch == g_lp
    karmic_compound = ch_tot in KARMIC_DEBTS

    # Expand remedy block when any flag fires (skill.md).
    needs_remedy = (
        karmic_compound
        or (not same_grp_bd and not same_grp_lp)
        or gap_lp >= 4
        or gap_bd >= 4
        or (ch_r != bd_r and ch_r != lp_r and not same_grp_bd and not same_grp_lp)
    )

    if same_grp_bd and same_grp_lp:
        alignment = "strong"
    elif same_grp_bd or same_grp_lp:
        alignment = "partial"
    else:
        alignment = "discordant"

    return {
        "bd_r": bd_r, "lp_r": lp_r, "ch_r": ch_r, "expr_r": expr_r,
        "g_bd": g_bd, "g_lp": g_lp, "g_ch": g_ch, "g_ex": g_ex,
        "gap_lp": gap_lp, "gap_bd": gap_bd,
        "same_grp_bd": same_grp_bd, "same_grp_lp": same_grp_lp,
        "karmic_compound": karmic_compound,
        "needs_remedy": needs_remedy,
        "alignment": alignment,
        "targets": _harmony_targets(bd, lp),
    }


def _consonant_skeleton(word: str) -> str:
    return "".join(c.upper() for c in word if c.upper() not in VOWELS)


def _normalize_skeleton(word: str) -> str:
    """Consonant backbone — collapse doubled consonants (Kummar ≈ Kumar)."""
    sk = _consonant_skeleton(word)
    out: list[str] = []
    for c in sk:
        if not out or out[-1] != c:
            out.append(c)
    return "".join(out)


def _letter_run_max(word: str) -> int:
    best = 1
    run = 1
    for i in range(1, len(word)):
        if word[i].lower() == word[i - 1].lower():
            run += 1
            best = max(best, run)
        else:
            run = 1
    return best


def _repeat_letter_edit(orig: str, new: str) -> bool:
    """`new` is `orig` with exactly one letter doubled, or one duplicate removed."""
    if orig == new:
        return False
    if len(new) == len(orig) + 1:
        for i in range(len(orig)):
            if new.lower() == (orig[: i + 1] + orig[i] + orig[i + 1 :]).lower():
                return True
        return False
    if len(new) == len(orig) - 1:
        for i in range(1, len(orig)):
            if orig[i].lower() == orig[i - 1].lower():
                if new.lower() == (orig[:i] + orig[i + 1 :]).lower():
                    return True
        return False
    return False


def _is_natural_spelling(spelling: str, original: str) -> bool:
    """Repeat-letter tweak only — same pronunciation, same letters in order."""
    orig_parts = original.split()
    new_parts = spelling.split()
    if len(orig_parts) != len(new_parts):
        return False
    changed = 0
    for o, n in zip(orig_parts, new_parts):
        if o == n:
            continue
        if not _repeat_letter_edit(o, n) or _letter_run_max(n) > 3:
            return False
        changed += 1
    return changed > 0


def _edit_magnitude(original: str, spelling: str) -> int:
    """How many letters were repeated (doubled) across the full name."""
    op = original.replace(" ", "")
    sp = spelling.replace(" ", "")
    if op == sp:
        return 0
    if len(sp) < len(op):
        return len(op) - len(sp) or 1
    i = j = doubles = 0
    while i < len(op) and j < len(sp):
        if (j + 1 < len(sp) and sp[j].lower() == sp[j + 1].lower()
                and op[i].lower() == sp[j].lower()):
            doubles += 1
            j += 2
            i += 1
        elif (i + 1 < len(op) and op[i].lower() == op[i + 1].lower()
              and op[i].lower() == sp[j].lower()):
            doubles += 1
            i += 2
            j += 1
        elif op[i].lower() == sp[j].lower():
            i += 1
            j += 1
        else:
            return 99
    if i != len(op):
        return 99
    doubles += max(0, len(sp) - j)
    return max(doubles, 1)


def _spelling_edits(word: str) -> list[tuple[str, str]]:
    """Repeat a letter already in the word — Riitesh, Rittesh, Riteesh (same sound)."""
    edits: list[tuple[str, str]] = []
    seen = {word.lower(): word}

    def add(sp: str, note: str) -> None:
        key = sp.lower()
        if not sp or not sp.isalpha() or key in seen:
            return
        seen[key] = sp
        edits.append((sp, note))

    for i, ch in enumerate(word):
        add(word[: i + 1] + ch + word[i + 1 :], f"repeat {ch.upper()} in {word}")

    for i in range(1, len(word)):
        if word[i].lower() == word[i - 1].lower():
            add(word[:i] + word[i + 1 :], f"drop repeated {word[i].upper()} in {word}")

    return edits


def _combine_parts(parts: list[str]) -> str:
    return " ".join(parts)


def _spelling_candidates(name: str, max_edits: int = 2) -> list[tuple[str, str]]:
    """Build natural spellings from up to `max_edits` phonetic tweaks across name parts."""
    name = name.strip()
    parts = name.split() or [name]
    options = [[(p, "unchanged")] for p in parts]
    for i, p in enumerate(parts):
        for sp, note in _spelling_edits(p):
            options[i].append((sp, note))

    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for combo in itertools.product(*options):
        new_parts = [c[0] for c in combo]
        notes = [c[1] for c in combo if c[1] != "unchanged"]
        if not notes:
            continue
        if len(notes) > max_edits:
            continue
        spelling = _combine_parts(new_parts)
        if spelling.upper() in seen or spelling.upper() == name.upper():
            continue
        if not _is_natural_spelling(spelling, name):
            continue
        seen.add(spelling.upper())
        out.append((spelling, "; ".join(notes)))
    return out


def suggest_name_corrections(name: str, targets: list[tuple[int, str, int]],
                             max_results: int = 4) -> list[dict]:
    """Chaldean tweaks by repeating letters already in the name (Avasthi)."""
    name = name.strip()
    if not name:
        return []
    cur_total = name_total(name, CHALDEAN)
    cur_root = _root(cur_total)
    target_roots = {t[0] for t in targets}
    candidates: list[dict] = []

    for spelling, note in _spelling_candidates(name):
        total = name_total(spelling, CHALDEAN)
        if not _valid_compound(total):
            continue
        root = _root(total)
        if root == cur_root:
            continue
        for t_root, t_reason, t_pri in targets:
            if root != t_root:
                continue
            extra = total - cur_total
            parts_changed = sum(
                1 for o, n in zip(name.split(), spelling.split()) if o != n)
            inserts = _edit_magnitude(name, spelling)
            if inserts > 4:
                continue
            candidates.append({
                "spelling": spelling,
                "added": note,
                "compound": total,
                "root": root,
                "reason": t_reason,
                "inserts": inserts,
                "score": (t_pri, inserts, parts_changed, len(spelling)),
            })
            break

    candidates.sort(key=lambda x: x["score"])
    out: list[dict] = []
    seen: set[str] = set()
    for cand in candidates:
        key = cand["spelling"].upper()
        if key in seen:
            continue
        seen.add(key)
        out.append(cand)
        if len(out) >= max_results:
            break
    return out


def _harmony_blend_text(h: dict, c: dict) -> str:
    """Ritz-style blend callout from group membership."""
    pieces = []
    if h["g_bd"] == h["g_ex"]:
        pieces.append(
            f"<strong>Birth-day {_root_label(c['birth_day'])}</strong> and "
            f"<strong>Expression {_root_label(c['expression'])}</strong> both sit in "
            f"<strong>Group {h['g_bd']}</strong> ({AVASTHI_THEME[h['g_bd']].split('(')[0].strip()}).")
    if h["g_lp"] == h["g_ch"]:
        pieces.append(
            f"Your <strong>Life Path {_root_label(c['life_path'])}</strong> and "
            f"<strong>Chaldean name {_root_label(c['chaldean_root'])}</strong> share "
            f"<strong>Group {h['g_lp']}</strong>.")
    if h["alignment"] == "discordant":
        pieces.append(
            f"Your <strong>Chaldean name root {planet_label(h['ch_r'])}</strong> sits in "
            f"<strong>Group {h['g_ch']}</strong> while Basic is <strong>Group {h['g_bd']}</strong> "
            f"and Destiny is <strong>Group {h['g_lp']}</strong> — the everyday name pulse and "
            f"birth pattern pull in different directions.")
    elif h["alignment"] == "partial":
        grp = "Basic" if h["same_grp_bd"] else "Destiny"
        g = h["g_bd"] if h["same_grp_bd"] else h["g_lp"]
        other = "Destiny" if grp == "Basic" else "Basic"
        og = h["g_lp"] if grp == "Basic" else h["g_bd"]
        pieces.append(
            f"Chaldean name aligns with <strong>{grp}</strong> (Group {g}) but not "
            f"<strong>{other}</strong> (Group {og}) — expect a rhythm between inner self and outer path.")
    if not pieces:
        pieces.append(
            "Your core numbers share compatible Avasthi groups — the name supports birth-day and path "
            "without a spelling correction being urgent.")
    return " ".join(pieces)


def _balance_number(name: str) -> tuple[int, str]:
    """Initials of each name word — Pythagorean, masters reduced (Woods)."""
    initials = [w[0].upper() for w in name.split() if w and w[0].isalpha()]
    if not initials:
        return 0, "?"
    total = sum(PYTHAG.get(ch, 0) for ch in initials)
    return _root(total), "".join(initials)


def _human_harmony_summary(c: dict, h: dict, title: str) -> str:
    if h["alignment"] == "strong":
        return (f"Your name <strong>{title}</strong> already harmonises with your birth numbers — "
                f"no spelling change needed.")
    if h["same_grp_bd"] or h["same_grp_lp"]:
        gap = "birth-day" if not h["same_grp_bd"] else "life path"
        return (f"Your name number <strong>{h['ch_r']}</strong> is close but not fully aligned with your {gap}. "
                f"Repeat a letter already in your name — like <em>Riitesh</em>, <em>Rittesh</em>, or <em>Riteesh</em> — "
                f"so it sounds the same when spoken.")
    return (f"Your name vibrates as <strong>{h['ch_r']} ({planet_name(h['ch_r'])})</strong> but your birth-day "
            f"is <strong>{_root_label(c['birth_day'])}</strong> and life path is <strong>{c['life_path']}</strong>. "
            f"Try doubling an existing letter in the spelling — same sound, different Chaldean total.")


def _human_snapshot(c: dict, pos: dict, h: dict) -> str:
    _, lp_desc = LIFE_PATH.get(c["life_path"], ("", ""))
    name_note = ("A repeat-letter spelling tweak may help — see below." if h["needs_remedy"]
                 else "Name and birth numbers are in reasonable harmony.")
    return (
        f"{_timing_narrative(c, pos)}"
        f"<br><br>Life path <strong>{c['life_path']}</strong> ({lp_desc.split(';')[0].lower()}) "
        f"— {name_note}"
    )


def _short_trait(text: str) -> str:
    return text.split("—")[0].strip().rstrip(".")


def _human_name_portrait(c: dict) -> str:
    expr = EXPRESSION.get(c["expression"], "")
    soul = SOUL_URGE.get(c["soul_urge"], "")
    pers = PERSONALITY.get(c["personality"], "")
    soul_short = _short_trait(soul)
    if soul_short.lower().startswith("for "):
        soul_clause = f"you want {soul_short[4:]}"
    else:
        soul_clause = f"you want {soul_short.lower()}"
    return (
        f"You come across as <strong>{_short_trait(pers)}</strong> (Personality {c['personality']}). "
        f"Your talent is <strong>{_short_trait(expr)}</strong> (Expression {c['expression']}). "
        f"Inside, {soul_clause} (Soul Urge {c['soul_urge']}). "
        f"The name you sign daily vibrates as <strong>{c['chaldean_root']} ({planet_name(c['chaldean_root'])})</strong>."
    )


def _remedy_section_html(c: dict, h: dict, title: str, pos: dict) -> str:
    """Compact harmony + phonetic name suggestions."""
    suggestions = suggest_name_corrections(c["name"], h["targets"], max_results=3) if h["needs_remedy"] else []
    bal_num, bal_init = _balance_number(c["name"])
    mc = pos["maha"]
    lines = [
        f'<p class="pred">{_human_harmony_summary(c, h, title)}</p>',
        f'<p class="pred">{_harmony_blend_text(h, c)}</p>',
    ]
    if h["karmic_compound"]:
        lines.append(
            f'<p class="pred">Your current name compound <strong>{c["chaldean_total"]}</strong> carries a '
            f'karmic tone — any new spelling should avoid 13, 14, 16, 19.</p>'
        )
    if h["needs_remedy"] and suggestions:
        items = "".join(
            f"<li>Write as <strong>{escape(s['spelling'])}</strong> "
            f"({escape(s['added'].lower())}) → name number "
            f"<strong>{s['root']} ({planet_name(s['root'])})</strong></li>"
            for s in suggestions
        )
        lines.append(
            '<h2>Spelling options (same sound)</h2>'
            '<p class="pred">Repeat a letter already in your name — pronunciation stays the same. '
            'Try on email, social profiles and cards for 30–90 days before any legal change:</p>'
            f'<ul>{items}</ul>'
        )
    elif h["needs_remedy"]:
        lines.append(
            '<p class="pred">No repeat-letter tweak reached a clean target — keep your current spelling, '
            'try a middle-name initial on daily documents, or consult a numerologist for a custom adjustment.</p>'
        )
    lines.append(
        f'<p class="pred"><strong>Under stress:</strong> initials <strong>{bal_init}</strong> → Balance {bal_num} — '
        f'{escape(BALANCE_TEXT.get(bal_num, ""))}</p>'
        f'<p class="pred"><strong>Timing:</strong> <strong>{mc["planet"]}</strong> chapter until {mc["end"]} — '
        f'{escape(_dasha_prediction(mc["num"], c, "maha"))}.</p>'
    )
    return "\n    ".join(lines)


# ───────────────────────── core computation ─────────────────────────
def compute(name: str, dob: date) -> dict:
    d = dob.day
    m = dob.month
    y = dob.year

    # Core numbers.
    lp_raw = sum(int(c) for c in f"{d:02d}{m:02d}{y}")
    life_path = reduce_num(lp_raw)
    birth_day = reduce_num(d)

    expr_total = name_total(name, PYTHAG)
    expression = reduce_num(expr_total)
    pers_total = name_total(name, PYTHAG, only="consonant")
    personality = reduce_num(pers_total)
    soul_total = name_total(name, PYTHAG, only="vowel")
    soul_urge = reduce_num(soul_total)

    chaldean_total = name_total(name, CHALDEAN)
    chaldean_root = reduce_num(chaldean_total, keep_master=False)

    # Hidden passion + karmic lessons from the Pythagorean letter breakdown.
    pyth_letters = letter_values(name, PYTHAG)
    freq = Counter(v for _, v in pyth_letters)
    hidden_passion = max(freq, key=lambda k: (freq[k], k)) if freq else None
    present_name_digits = set(freq)
    karmic_lessons = [n for n in range(1, 10) if n not in present_name_digits]

    # Karmic debts: any core compound landing on 13/14/16/19.
    debts = {}
    for label, total in (("Life Path", lp_raw), ("Expression", expr_total),
                         ("Personality", pers_total), ("Soul Urge", soul_total),
                         ("Chaldean name", chaldean_total), ("Birth-day", d)):
        if total in KARMIC_DEBTS:
            debts[label] = total

    maturity = reduce_num(reduce_num(life_path, keep_master=False)
                          + reduce_num(expression, keep_master=False),
                          keep_master=False)

    # Challenges (masters reduced before subtracting).
    rm, rd, ry = (reduce_num(m, keep_master=False), reduce_num(d, keep_master=False),
                  reduce_num(y, keep_master=False))
    c1 = abs(rm - rd)
    c2 = abs(rd - ry)
    c3 = abs(c1 - c2)
    c4 = abs(rm - rd)  # per OCR (duplicates 1st); standard uses |month-year|.
    c4_std = abs(rm - ry)

    # Pinnacles (Woods): pivot age = 36 − LP root; numbers P1=m+d, P2=d+y, P3=P1+P2, P4=m+y.
    lp_root = reduce_num(life_path, keep_master=False)
    pin_age1 = 36 - lp_root
    p_nums = [reduce_num(rm + rd), reduce_num(rd + ry),
              reduce_num(reduce_num(rm + rd, keep_master=False)
                         + reduce_num(rd + ry, keep_master=False)),
              reduce_num(rm + ry)]
    pin_ages = [(0, pin_age1), (pin_age1, pin_age1 + 9),
                (pin_age1 + 9, pin_age1 + 18), (pin_age1 + 18, None)]

    # Lo Shu (with century) vs Vedic Ank Kundli (no century); drop zeros.
    loshu_digits = [int(c) for c in f"{d:02d}{m:02d}{y}" if c != "0"]
    ank_digits = [int(c) for c in f"{d:02d}{m:02d}{y % 100:02d}" if c != "0"]

    return {
        "name": name, "dob": dob,
        "life_path": life_path, "life_path_raw": lp_raw, "lp_root": lp_root,
        "birth_day": birth_day, "day": d, "month": m, "year": y,
        "expression": expression, "expr_total": expr_total,
        "personality": personality, "pers_total": pers_total,
        "soul_urge": soul_urge, "soul_total": soul_total,
        "chaldean_total": chaldean_total, "chaldean_root": chaldean_root,
        "pyth_letters": pyth_letters, "chaldean_letters": letter_values(name, CHALDEAN),
        "hidden_passion": hidden_passion, "karmic_lessons": karmic_lessons,
        "karmic_debts": debts, "maturity": maturity,
        "challenges": [c1, c2, c3, c4], "challenge4_std": c4_std,
        "rm": rm, "rd": rd, "ry": ry,
        "pinnacle_nums": p_nums, "pinnacle_ages": pin_ages, "pin_age1": pin_age1,
        "loshu": Counter(loshu_digits), "ank": Counter(ank_digits),
        "maha": maha_dasha(dob), "lucky": LUCKY_SERIES[lp_root],
    }


def maha_dasha(dob: date) -> list[dict]:
    """45-year cycle: start = birthday root (reduced day), period length = the number,
    sequence increments wrapping 9→1; ring then repeats."""
    start = reduce_num(dob.day, keep_master=False)
    seq = [(start - 1 + i) % 9 + 1 for i in range(11)]  # two cycles' worth for the table
    rows = []
    yr = dob.year
    for num in seq:
        rows.append({"num": num, "planet": PLANET[num], "start": yr, "end": yr + num,
                     "theme": MAHA_THEME[num]})
        yr += num
    return rows


def antar_number(dob: date, year: int) -> tuple[int, int, int]:
    """Return (antar_number, weekday_index, weekday_lord) for the birthday in `year`."""
    bday = date(year, dob.month, dob.day)
    wd = bday.weekday()
    lord = WEEKDAY_LORD[wd]
    n = reduce_num(reduce_num(year, keep_master=False)
                   + reduce_num(dob.month, keep_master=False)
                   + reduce_num(dob.day, keep_master=False) + lord, keep_master=False)
    return n, wd, lord


def pratyantar(start: date, antar_num: int) -> list[dict]:
    """Nine unequal slices; lords start on antar_num, +1 wrapping 9→1; length = (lord/45)*365
    with largest-remainder rounding so they sum to the year."""
    lords = [(antar_num - 1 + i) % 9 + 1 for i in range(9)]
    exact = [l / 45 * 365 for l in lords]
    days = [int(x) for x in exact]
    rem = 365 - sum(days)
    order = sorted(range(9), key=lambda i: exact[i] - days[i], reverse=True)
    for i in range(rem):
        days[order[i]] += 1
    rows, cur = [], start
    for lord, dur in zip(lords, days):
        nxt = cur + timedelta(days=dur)
        rows.append({"num": lord, "planet": PLANET[lord], "start": cur,
                     "end": nxt - timedelta(days=1)})
        cur = nxt
    return rows


def current_position(c: dict, as_of: date) -> dict:
    dob = c["dob"]
    # Current Maha row.
    maha_cur = next((r for r in c["maha"] if r["start"] <= as_of.year < r["end"]), c["maha"][0])
    # Current Antar (birthday) year.
    this_bday = date(as_of.year, dob.month, dob.day)
    antar_year = as_of.year if as_of >= this_bday else as_of.year - 1
    antar_n, wd, lord = antar_number(dob, antar_year)
    prev_n, pwd, plord = antar_number(dob, antar_year - 1)
    praty = pratyantar(date(antar_year, dob.month, dob.day), antar_n)
    praty_cur = next((p for p in praty if p["start"] <= as_of <= p["end"]), praty[0])
    return {"maha": maha_cur, "antar_year": antar_year, "antar_n": antar_n,
            "antar_wd": wd, "antar_lord": lord, "prev_antar_n": prev_n,
            "praty": praty, "praty_cur": praty_cur}


# ───────────────────────── HTML rendering ─────────────────────────
def fmt_date(d: date) -> str:
    return f"{d.day} {d.strftime('%B')} {d.year}"


def fmt_short(d: date) -> str:
    return f"{d.day} {d.strftime('%b')}"


def slugify(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", name.strip()).strip("_")
    return s or "Client"


def _nameblock(letters: list[tuple[str, int]]) -> str:
    top = "   ".join(ch for ch, _ in letters)
    bot = "   ".join(str(v) for _, v in letters)
    return f"{top}\n{bot}"


def render_html(c: dict, sex: str, as_of: date) -> str:
    dob = c["dob"]
    pos = current_position(c, as_of)
    age = as_of.year - dob.year - ((as_of.month, as_of.day) < (dob.month, dob.day))
    def planet(n):
        return planet_label(n)

    # Maha table — current chapter + next two only.
    maha_cur_idx = next((i for i, r in enumerate(c["maha"]) if r["start"] <= as_of.year < r["end"]), 0)
    maha_rows = []
    for r in c["maha"][maha_cur_idx: maha_cur_idx + 3]:
        cur = r["start"] <= as_of.year < r["end"]
        feel = _dasha_prediction(r["num"], c, "maha")
        cells = (f"{r['start']} – {r['end']}", r["planet"],
                 ("<strong>Now:</strong> " if cur else "") + feel)
        if cur:
            cells = (f"<strong>{cells[0]}</strong>", f"<strong>{cells[1]}</strong>", cells[2])
        maha_rows.append("<tr>" + "".join(f"<td>{x}</td>" for x in cells) + "</tr>")

    # Antar window — current year ±2.
    antar_rows = []
    for yr in range(pos["antar_year"] - 2, pos["antar_year"] + 3):
        n, wd, lord = antar_number(dob, yr)
        cur = yr == pos["antar_year"]
        feel = _dasha_prediction(n, c, "antar")
        cells = (f"{yr}", planet_name(n),
                 ("<strong>This year:</strong> " if cur else "") + feel)
        if cur:
            cells = (f"<strong>{cells[0]}</strong>", f"<strong>{cells[1]}</strong>", cells[2])
        antar_rows.append("<tr>" + "".join(f"<td>{x}</td>" for x in cells) + "</tr>")

    # Pratyantar — current slice + up to two following (or preceding if at year-end).
    praty_cur_idx = next((i for i, p in enumerate(pos["praty"]) if p is pos["praty_cur"]), 0)
    praty_slice = pos["praty"][praty_cur_idx: praty_cur_idx + 3]
    if len(praty_slice) < 3:
        praty_slice = pos["praty"][max(0, praty_cur_idx - (3 - len(praty_slice))): praty_cur_idx + 3]
    praty_rows = []
    for p in praty_slice:
        cur = p is pos["praty_cur"]
        rng = f"{fmt_short(p['start'])} – {fmt_short(p['end'])} {p['end'].year}"
        feel = _dasha_prediction(p["num"], c, "praty")
        cells = (p["planet"], rng, ("<strong>Now:</strong> " if cur else "") + feel)
        if cur:
            cells = (f"<strong>{cells[0]}</strong>", f"<strong>{cells[1]}</strong>", cells[2])
        praty_rows.append("<tr>" + "".join(f"<td>{x}</td>" for x in cells) + "</tr>")

    # Lo Shu / Ank grids.
    def grid_table(counts: Counter) -> str:
        layout = [[4, 9, 2], [3, 5, 7], [8, 1, 6]]
        out = []
        for row in layout:
            out.append("<tr>" + "".join(f"<th>{n}</th>" for n in row) + "</tr>")
            out.append("<tr>" + "".join(f"<td>{counts.get(n, 0)}</td>" for n in row) + "</tr>")
        return "<table class=\"grid\">" + "".join(out) + "</table>"

    loshu_missing, raw_loshu_missing, pillar_only = _effective_grid_missing(c)
    ank_missing = _ank_grid_missing(c)
    pillar_note = ""
    if pillar_only:
        bits = []
        for n in sorted(pillar_only):
            if n == _root(c["birth_day"]):
                bits.append(f"Basic {n} ({PLANET[n]})")
            elif n == _root(c["life_path"]):
                bits.append(f"Destiny {n} ({PLANET[n]})")
            else:
                bits.append(f"{n} ({PLANET[n]})")
        pillar_note = (
            f"<p class=\"fine\">Per Avasthi Ank Kundli rules, your "
            f"{', '.join(bits)} {'is' if len(bits) == 1 else 'are'} placed in the grid even when "
            f"{'it does' if len(bits) == 1 else 'they do'} not appear in the raw birth-date tally — "
            f"so {'it is' if len(bits) == 1 else 'they are'} not treated as missing.</p>"
        )

    # Karmic debt boxes.
    debt_boxes = ""
    for label, total in c["karmic_debts"].items():
        debt_boxes += (f'<div class="karmic-box"><strong>Karmic Debt {total} '
                       f'({label}):</strong> {escape(KARMIC_DEBT_TEXT[total])}</div>')

    lp_label, lp_desc = LIFE_PATH.get(c["life_path"], ("a life path", ""))
    hp = c["hidden_passion"]
    missing_lines = _missing_remedy_lines(loshu_missing)
    name_karmic_html = ""
    if c["karmic_lessons"]:
        kl_items = "".join(
            f"<li><strong>Name lesson {n}:</strong> {escape(KARMIC_LESSON_WOODS[n])}</li>"
            for n in c["karmic_lessons"]
        )
        name_karmic_html = (
            "<h2>Name karmic lessons</h2>"
            "<p class=\"fine\">Digits absent from your name spelling — separate from birth-grid gaps.</p>"
            f"<ul>{kl_items}</ul>"
        )
    grid_html = grid_table(_effective_loshu_counts(c))
    strong_html = _strong_digits_text(c)
    period_remedy_html = _period_remedy_line(pos)
    # Harmony table.
    harmony_rows = "".join(
        f"<tr><td>{lbl}</td><td><strong>{planet(val)}</strong></td>"
        f"<td>Group {avasthi_group(val)} — {', '.join(map(str, AVASTHI_GROUPS[avasthi_group(val)]))}</td></tr>"
        for lbl, val in (("Basic (birth-day)", c["birth_day"]),
                         ("Destiny / Life Path", reduce_num(c["life_path"], keep_master=False)),
                         ("Chaldean Name root", c["chaldean_root"]),
                         ("Expression (Pythagorean)", reduce_num(c["expression"], keep_master=False))))

    pin_idx = next(
        (i for i, (a0, a1) in enumerate(c["pinnacle_ages"])
         if age < (a1 if a1 is not None else 999) and age >= a0),
        len(c["pinnacle_ages"]) - 1,
    )
    pin_num = c["pinnacle_nums"][pin_idx]
    pin_band = c["pinnacle_ages"][pin_idx]
    pin_label = ["1st", "2nd", "3rd", "4th"][pin_idx]
    pin_range = (f"birth to ~{pin_band[1]}" if pin_idx == 0 else
                 (f"~{pin_band[0]} onward" if pin_band[1] is None else f"~{pin_band[0]} to ~{pin_band[1]}"))
    ch_main = c["challenges"][2]

    lucky = ", ".join(str(x) for x in c["lucky"])
    lucky_short = ", ".join(str(x) for x in c["lucky"][:6])
    universal = ", ".join(str(x) for x in LUCKY_SERIES[5][:6])
    harmony = assess_name_harmony(c)
    mc = pos["maha"]

    css = _CSS
    title = escape(c["name"])
    remedy_html = _remedy_section_html(c, harmony, title, pos)
    parts = []
    parts.append(f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Numerology Report — {title}</title>
  <style>{css}</style>
</head>
<body>
  <article class="card">
    <h1 style="color:var(--heading);">Numerology reading</h1>
    <div class="callout-amber"><strong>⚠ Uncalibrated — first pass.</strong> Numbers and cycles are computed from name + birth date; life-event dates were not supplied to validate timing against your history.</div>
    <dl class="meta">
      <dt>Name</dt><dd>{title}</dd>
      <dt>Sex</dt><dd>{escape(sex)}</dd>
      <dt>Date of birth</dt><dd>{fmt_date(dob)}</dd>
      <dt>Report date</dt><dd>{fmt_date(as_of)}</dd>
    </dl>
    <p class="lead">A plain-English numerology reading from your name and birth date. For reflection only — not medical, legal, or financial advice.</p>
    <div class="callout">{_human_snapshot(c, pos, harmony)}</div>''')

    parts.append(f'''
    <h1>Your core numbers</h1>
    <table class="compact">
      <tr><th>What</th><th>Number</th><th>Meaning in plain words</th></tr>
      <tr><td>Birth-day</td><td><strong>{planet(c['birth_day'])}</strong></td><td>How you see yourself; inner nature</td></tr>
      <tr><td>Life path</td><td><strong>{planet(c['life_path'])}</strong></td><td>{escape(lp_desc.split(';')[0])}</td></tr>
      <tr><td>Name (Chaldean)</td><td><strong>{planet(c['chaldean_root'])}</strong></td><td>Everyday vibration of the name you sign</td></tr>
      <tr><td>Expression</td><td><strong>{planet(c['expression'])}</strong></td><td>How the world reads your talent</td></tr>
    </table>''')

    parts.append(f'''
    <h1>Life forecast</h1>
    <h2>Lo Shu grid (birth date + pillars placed)</h2>
    {grid_html}
    {strong_html}
    <p class="pred"><strong>Work &amp; money:</strong> Life path {c['life_path']} — {escape(lp_desc.split(';')[0].lower())}. {escape(_birthday_money(c['birth_day']))} This birthday year ({planet_name(pos['antar_n'])}): {escape(_dasha_prediction(pos['antar_n'], c, 'antar'))}</p>
    <p class="pred"><strong>Love &amp; bonds:</strong> {escape(_love_by_planet(mc['num']))} Partners who share your number group (see harmony below) tend to understand you more easily.</p>
    <p class="pred"><strong>Health &amp; energy:</strong> {escape(MISSING_DIGIT[loshu_missing[0]][1]) if loshu_missing else 'Your core grid pillars are well placed — keep steady routines.'} The current {mc['planet']} chapter rewards pacing yourself.</p>
    <p class="pred"><strong>Your name:</strong> {_human_name_portrait(c)}</p>
    {debt_boxes}''')

    parts.append(f'''
    <h1>Timing — what is active now</h1>
    <p class="fine">Mahā = major chapter (years). Antar = flavour of each birthday year. Pratyantar = month-scale slice inside the year. Wording follows Avasthi <em>Ank Jyotish</em> dasha results and adjusts when a digit is open vs already in your chart.</p>
    <h2>Major life chapters</h2>
    <table class="dasha">
      <tr><th>Period</th><th>Planet</th><th>What it feels like</th></tr>
      {''.join(maha_rows)}
    </table>
    <h2>Year-by-year tone</h2>
    <table class="dasha">
      <tr><th>Year</th><th>Planet</th><th>Flavour</th></tr>
      {''.join(antar_rows)}
    </table>
    <h2>Months ahead (current birthday year)</h2>
    <table class="dasha">
      <tr><th>Planet</th><th>Dates</th><th>Best for</th></tr>
      {''.join(praty_rows)}
    </table>''')

    parts.append(f'''
    <h1>Name harmony &amp; remedies</h1>
    <table class="compact">
      <tr><th>Number</th><th>Value</th><th>Group</th></tr>
      {harmony_rows}
    </table>
    {remedy_html}
    <p class="pred"><strong>Lucky numbers for you:</strong> {lucky_short} … (full series in appendix). Avoid <strong>18</strong> in relationship choices.</p>
    {pillar_note}
    <h2>Open grid digits — practical support</h2>
    <p class="fine">Avasthi (p.77) treats missing numbers as secondary to dashā and strengths. Below: lifestyle habits plus colour/charity/gem notes from the Book of Remedies (rules41). Gemstones are optional — not prescribed for every chart; test reactive stones (especially Saturn/Neelam) before long wear.</p>
    <ul>{missing_lines or '<li>Your birth grid has no major gaps once Basic and Destiny are placed.</li>'}</ul>
    {name_karmic_html}
    {period_remedy_html}
    <p class="note">Remedies are for reflection — not medical, legal, or financial instructions. Wind chimes, rod-count objects, and similar items are <strong>not</strong> in the numerology OCR sources used here.</p>''')

    parts.append(f'''
    <h1>Life chapter you are in now</h1>
    <p class="pred">At age <strong>{age}</strong>, you are in your <strong>{pin_label} pinnacle ({pin_num})</strong> — {pin_range}. Theme: {escape(_pinnacle_theme(pin_num))}.</p>
    <p class="pred">Main life challenge (number <strong>{ch_main}</strong>): {escape(CHALLENGE_THEME[ch_main])}</p>
    <p class="pred">From ~age 35, maturity number <strong>{c['maturity']}</strong> grows stronger: {escape(_maturity_text(c['maturity']))}</p>''')

    # Appendix.
    parts.append(f'''
    <h1>Appendix — key figures</h1>
    <div class="appendix">
      <p><strong>Chaldean name (Avasthi, for harmony/correction):</strong></p>
      <div class="nameblock">{escape(_nameblock(c['chaldean_letters']))}
Compound {c['chaldean_total']} → root <strong>{c['chaldean_root']}</strong></div>
      <p><strong>Pythagorean name (soul portrait):</strong></p>
      <div class="nameblock">{escape(_nameblock(c['pyth_letters']))} → {c['expr_total']} → Expression <strong>{c['expression']}</strong>
Consonants → {c['pers_total']} → Personality <strong>{c['personality']}</strong>
Vowels → {c['soul_total']} → Soul Urge <strong>{c['soul_urge']}</strong></div>
      <p><strong>Birth-day number:</strong> {c['birth_day']} &nbsp;|&nbsp; <strong>Path number:</strong> {c['life_path']} ({'+'.join(f"{ch}" for ch in f"{dob.day:02d}{dob.month:02d}{dob.year}")} = {c['life_path_raw']} → {c['life_path']})</p>
      <p><strong>Maturity number:</strong> LP {c['lp_root']} + Expression {reduce_num(c['expression'], keep_master=False)} = {c['maturity']} (masters reduced). Onset ~age 35.</p>
      <p><strong>4th Challenge formula caution:</strong> the OCR source uses |month − day| (same as the 1st challenge); standard literature uses |month − year| = |{c['rm']} − {c['ry']}| = <strong>{c['challenge4_std']}</strong>. Treat the 4th as either {c['challenges'][3]} or {c['challenge4_std']} pending a paper-copy verification.</p>
      <p><strong>Antar formula:</strong> digit-sum of calendar year (reduced) + birth month + birth day + weekday lord of that year's birthday → reduce.</p>
      <p><strong>Pratyantar:</strong> nine unequal slices; order begins on the Antar lord, cycles +1 wrapping 9→1; each slice = (lord ÷ 45) × 365 days, largest-remainder rounding.</p>
      <p><strong>Lucky series (LP {c['lp_root']}):</strong> {lucky}. Universal 5-series: {universal}… Avoid 18 in relationships.</p>
      <p><strong>Lo Shu grid (birth-date tally, century included):</strong> raw gaps {', '.join(map(str, raw_loshu_missing)) or 'none'}.</p>
      <p><strong>Avasthi grid (Basic + Destiny placed per book):</strong> open digits {', '.join(map(str, loshu_missing)) or 'none'}; Ank Kundli (no century) open digits {', '.join(map(str, ank_missing)) or 'none'}.</p>
    </div>
    <p class="note">Numerology is a mirror for timing and temperament, not a guarantee. Use good judgment in money, health, and relationships.</p>
  </article>
</body>
</html>''')
    return "".join(parts)


# Supporting interpretation helpers.
CHALLENGE_THEME = {
    0: "All-or-nothing pure potential — you must choose your own direction without a built-in pressure to react.",
    1: "Develop independence and the courage of your own decisions; resist over-reliance on others.",
    2: "Develop cooperation, patience and emotional diplomacy; lead without isolating.",
    3: "Develop authentic self-expression and joyful creativity; let yourself be heard, not just effective.",
    4: "Develop order and follow-through; shortcuts backfire — the work itself is the answer.",
    5: "Find genuine freedom within responsibility — restlessness is the growing edge, not an excuse.",
    6: "Develop healthy responsibility and standards without perfectionism or martyrdom.",
    7: "Develop trust and openness; depth is a gift, but don't wall yourself off.",
    8: "Develop a healthy relationship with money and power — use authority fairly.",
}


def _pin_compound(c: dict, i: int) -> int:
    rm, rd, ry = c["rm"], c["rd"], c["ry"]
    return [rm + rd, rd + ry, (rm + rd) + (rd + ry), rm + ry][i]


def _pinnacle_theme(num: int) -> str:
    base = {
        1: "independence, initiative and self-definition",
        2: "partnership, sensitivity and cooperation",
        3: "creative expression, optimism and social life",
        4: "building, structure and disciplined foundations",
        5: "freedom, change, travel and versatility",
        6: "home, responsibility, love and service",
        7: "study, depth, specialism and inner growth",
        8: "authority, money, legacy and material balance",
        9: "compassion, completion and broad humanitarian reach",
        11: "high intuition, spiritual sensitivity and inspired creativity",
        22: "large-scale building that serves many",
        33: "teaching and healing through care",
    }
    return base.get(num, "growth")


def _birthday_money(n: int) -> str:
    return {
        1: "rewards come through leadership and bold first moves.",
        2: "rewards come through partnership, patience and supportive roles.",
        3: "rewards come through communication, creativity and visibility.",
        4: "rewards come through steady method and dependable systems.",
        5: "rewards come through deals, networks and adaptability.",
        6: "rewards come through service, beauty and trusted relationships.",
        7: "rewards come through expertise, research and specialised knowledge.",
        8: "money and position arrive through effort and time — one long career wall, built brick by brick.",
        9: "rewards come through wide reach, causes and completing big projects.",
    }.get(reduce_num(n, keep_master=False), "rewards follow consistent effort.")


def _love_by_planet(n: int) -> str:
    return {
        1: "you lead in love — let partners have a voice too.",
        2: "bonds are central and tender; protect them from moodiness.",
        3: "warmth and fun flow — keep promises behind the charm.",
        4: "loyalty and stability matter most; make room for spontaneity.",
        5: "variety and freedom attract you; commitment needs conscious choice.",
        6: "home, marriage and harmony are favoured; watch over-giving.",
        7: "bonds deepen honestly or thin out; pressure tactics backfire.",
        8: "you take relationships seriously; balance ambition with presence.",
        9: "love is generous and idealistic; ground it in daily care.",
    }.get(n, "relationships ask for honesty and presence.")


def _maturity_text(n: int) -> str:
    return {
        1: "leadership and independent direction become the second-half theme.",
        2: "partnership, peace-making and quiet influence grow in importance.",
        3: "creative expression and communication flower more fully.",
        4: "stability, legacy and dependable structures matter more.",
        5: "freedom, adaptability and fresh experience keep you young.",
        6: "family, responsibility and service become central.",
        7: "wisdom, depth and inner life come to the fore.",
        8: "authority, long-form outcomes and material balance matter more than clever experiments alone.",
        9: "compassion, mentoring and giving back define the later years.",
    }.get(n, "your core themes mature and integrate.")


def _karmic_lesson_text(c: dict) -> str:
    kl = c["karmic_lessons"]
    if not kl:
        return ("Every digit 1–9 appears in your name — no single karmic lesson dominates; "
                "your name supplies a full toolkit.")
    names = ", ".join(str(n) for n in kl)
    return (f"The digits {names} are absent in your name's letter values, so the qualities they "
            f"carry must be developed on purpose rather than arriving by accident. Use calendars, "
            f"coaches and deliberate practice to supply what the name does not spell out.")


_CSS = """
    :root { --magenta:#b0106b; --heading:#0d47a1; --namegreen:#1b5e20; --text:#1a1a1a; --muted:#555; --bg:#fafafa; --card:#fff; --border:#e0e0e0; }
    * { box-sizing: border-box; }
    body { font-family: Georgia, "Times New Roman", serif; line-height:1.55; color:var(--text); background:var(--bg); margin:0; padding:1.5rem; max-width:48rem; margin-inline:auto; }
    .card { background:var(--card); border:1px solid var(--border); border-radius:6px; padding:1.5rem 1.75rem; box-shadow:0 1px 3px rgba(0,0,0,.06); }
    .meta { color:var(--magenta); font-size:1.05rem; margin-bottom:1rem; }
    .meta dt { font-weight:bold; margin-top:.35rem; } .meta dd { margin:0; }
    h1 { font-size:1.3rem; color:var(--heading); border-bottom:2px solid var(--heading); padding-bottom:.35rem; margin-top:1.75rem; }
    h1:first-of-type { margin-top:0; border:none; padding:0; }
    h2 { font-size:1.12rem; color:var(--heading); margin-top:1.2rem; margin-bottom:.45rem; }
    h3 { font-size:1.02rem; color:var(--heading); margin-top:.9rem; }
    .lead { font-size:1.05rem; margin-bottom:1rem; }
    .pred { margin:.65rem 0; }
    .callout { background:#e8f4fd; border-left:4px solid var(--heading); padding:.75rem 1rem; margin:1rem 0; font-size:0.98rem; }
    .callout-amber { background:#fff8e1; border-left:4px solid #f9a825; padding:.75rem 1rem; margin:1rem 0; font-size:0.98rem; }
    .callout-green { background:#e8f5e9; border-left:4px solid #2e7d32; padding:.75rem 1rem; margin:1rem 0; font-size:0.98rem; }
    table.dasha, table.grid, table.compact, table.challenge { width:100%; border-collapse:collapse; font-size:0.88rem; margin:.6rem 0 1rem; }
    table.dasha th, table.dasha td, table.grid th, table.grid td, table.compact th, table.compact td, table.challenge th, table.challenge td { border:1px solid var(--border); padding:.4rem .45rem; vertical-align:top; }
    table.dasha th, table.compact th, table.challenge th { background:#e3f2fd; color:var(--heading); text-align:left; }
    table.grid th { background:#e8f5e9; color:var(--namegreen); text-align:center; } table.grid td { text-align:center; }
    .note { font-size:0.85rem; color:var(--muted); margin-top:1rem; }
    .appendix { font-size:0.9rem; color:var(--muted); }
    .nameblock { font-family: ui-monospace,"Cascadia Code",Consolas,monospace; color:var(--namegreen); font-size:0.9rem; white-space:pre; margin:.5rem 0; line-height:1.35; }
    .karmic-box { background:#fce4ec; border-left:4px solid #c62828; padding:.65rem 1rem; margin:.8rem 0; font-size:0.95rem; }
    ul li { margin:.35rem 0; }
    .tag { display:inline-block; background:#e3f2fd; color:var(--heading); border-radius:3px; padding:.1rem .35rem; font-size:0.8rem; font-weight:bold; }
"""


def generate_numerology_html(name: str, dob: date, sex: str = "—",
                             report_date: date | None = None) -> tuple[str, str]:
    as_of = report_date or date.today()
    c = compute(name, dob)
    html = render_html(c, sex, as_of)
    slug = slugify(name)
    return html, slug


def _parse_date(s: str) -> date:
    return date.fromisoformat(s)


def main() -> None:
    ap = argparse.ArgumentParser(description="Deterministic numerology report (no LLM)")
    ap.add_argument("--name", required=True)
    ap.add_argument("--dob", required=True, type=_parse_date, help="YYYY-MM-DD")
    ap.add_argument("--sex", default="—")
    ap.add_argument("--report-date", type=_parse_date, default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    html, slug = generate_numerology_html(args.name, args.dob, args.sex, args.report_date)
    out = args.out or f"reports/Numerology_{slug}_{args.dob.isoformat()}.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
