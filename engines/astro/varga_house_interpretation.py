#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Human, prediction-first house readings for D1–D7 divisional charts."""
from __future__ import annotations

from typing import Any

from astro_precompute import SIGN_LORDS, get_dignity, house_sign

GRAHAS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")
_BENEFICS = frozenset({"Moon", "Mercury", "Jupiter", "Venus"})
_MALEFICS = frozenset({"Sun", "Mars", "Saturn", "Rahu", "Ketu"})
_TRIK = frozenset({6, 8, 12})

_DIGNITY_WORD = {
    "exalted": "very strong",
    "own_sign": "solid",
    "moolatrikona": "powerful",
    "great_friend_sign": "well supported",
    "friendly": "fairly good",
    "neutral_sign": "average",
    "neutral": "average",
    "enemy_sign": "under pressure",
    "debilitated": "weak",
    "unknown": "unclear",
}

# Human section titles (not book jargon)
HOUSE_LABELS: dict[tuple[str, int], str] = {
    **{( "D1", h): t for h, t in {
        1: "You — body, personality & life direction",
        2: "Money, family & speech",
        3: "Younger siblings, courage & communication",
        4: "Mother, home, property & peace of mind",
        5: "Children, creativity & intelligence",
        6: "Health, enemies, debt & daily struggle",
        7: "Marriage, partner & business partnerships",
        8: "Longevity, sudden changes & inheritance",
        9: "Father, luck, religion & long travel",
        10: "Career, status & public reputation",
        11: "Elder siblings, income & gains",
        12: "Expenses, foreign lands & spiritual retreat",
    }.items()},
    **{( "D2", h): t for h, t in {
        1: "Your financial constitution",
        2: "Savings, family wealth & spending habits",
        3: "Earning through effort, skills & initiative",
        4: "Property, vehicles & comfort from wealth",
        5: "Speculation, luck & smart money moves",
        6: "Debts, financial stress & money rivals",
        7: "Wealth through partners & contracts",
        8: "Inheritance, windfalls & financial shocks",
        9: "Fortune, ease of earning & father's role in wealth",
        10: "Career income & status through money",
        11: "Income streams & financial gains",
        12: "Expenses, losses & where money leaks",
    }.items()},
    **{( "D3", h): t for h, t in {
        1: "Your nature, body & sibling promise overall",
        2: "Family resources & speech among siblings",
        3: "Younger siblings, courage & bold action",
        4: "Happiness shared with siblings",
        5: "Second younger sibling & planning mind",
        6: "Obstacles, rivalry & sibling health stress",
        7: "Desires, partnerships & sibling-related bonds",
        8: "Longevity stress, crises & sibling loss themes",
        9: "Elder siblings, luck & support from them",
        10: "Career action & siblings' public path",
        11: "Elder co-born, gains & fulfilment through siblings",
        12: "Distance, separation & end of sibling karma",
    }.items()},
    **{( "D4", h): t for h, t in {
        1: "Your capacity for happiness & owning property",
        2: "Family money for home & domestic speech",
        3: "Courage in property matters & sibling share in assets",
        4: "Mother, home, land, vehicles & inner peace",
        5: "Joy from property, children at home",
        6: "Disputes, debts & obstacles to domestic peace",
        7: "Spouse's role in home & property deals",
        8: "Sudden property changes & inheritance stress",
        9: "Fortune in property, father & change of residence",
        10: "Career-linked property & built assets",
        11: "Gains from property & elder sibling's share",
        12: "Loss of property, spend on home & living abroad",
    }.items()},
    **{( "D7", h): t for h, t in {
        1: "Your capacity as a parent & progeny constitution",
        2: "Children's wealth, speech & family continuation",
        3: "Children's courage, siblings among children",
        4: "Children's happiness, education & mother's bond",
        5: "Birth of children & parent–child relationship",
        6: "Conception obstacles & children's health rivals",
        7: "Children's marriage & progeny from second union",
        8: "Children's longevity & hidden progeny stress",
        9: "Grandchildren & fortune through children",
        10: "Children's career & public standing",
        11: "Fulfilment of progeny wishes & children's success",
        12: "Separation from children & foreign settlement of progeny",
    }.items()},
    **{( "D9", h): t for h, t in {
        1: "Your inner self in marriage & how you show up as a partner",
        2: "Marital wealth, family values & speech in the union",
        3: "Courage, initiative & communication in partnership",
        4: "Marital happiness, home peace & emotional comfort after wedding",
        5: "Romance, affection, children after marriage & creative bond",
        6: "Obstacles, health stress & rivals affecting marriage",
        7: "Spouse, marriage quality & partnership itself",
        8: "Mangalya, longevity themes & hidden side of marriage",
        9: "Dharma in marriage, luck through spouse & spiritual path",
        10: "Spouse's career, your public image as a couple & karma",
        11: "Gains through marriage & fulfilment of partnership wishes",
        12: "Bed pleasure, foreign spouse, expenses & spiritual retreat in union",
    }.items()},
}


def _ordinal(n: int) -> str:
    if n == 1:
        return "1st"
    if n == 2:
        return "2nd"
    if n == 3:
        return "3rd"
    return f"{n}th"


# Register concise house labels for higher vargas (D10-D60) from the book corpus.
try:
    from divisional_book_corpus import HIGHER_VARGA_CORPUS as _HVC

    def _short_label(text: str) -> str:
        frag = text.split("—")[0].split(".")[0].strip()
        for sep in (" and ", ",", ";"):
            if sep in frag:
                frag = frag.split(sep)[0].strip()
                break
        return frag[:48] if frag else ""

    for _v, _c in _HVC.items():
        for _h, _sig in (_c.get("house_sigs") or {}).items():
            HOUSE_LABELS.setdefault((_v, _h), _short_label(_sig) or f"House {_h}")
except Exception:  # noqa: BLE001 - corpus optional at import
    pass


def _short_topic(varga: str, h: int) -> str:
    label = HOUSE_LABELS.get((varga, h), "this area")
    return label.split("—")[0].split("&")[0].split(",")[0].strip().lower()


def _dig_word(d: str) -> str:
    return _DIGNITY_WORD.get(d, "average")


def _lord_channel(varga: str, subject_h: int, lord_h: int | None) -> str:
    """How the house lord's placement colours results — varga- and topic-aware."""
    if not lord_h:
        return ""
    key = (varga, subject_h, lord_h)
    specific = _LORD_CHANNEL_SPECIFIC.get(key)
    if specific:
        return specific
    generic = {
        1: "matters loop back to your own body, mood, and life direction",
        2: "money, family speech, and stored resources are involved",
        3: "younger siblings, courage, and short moves colour the result",
        4: "home, mother, and emotional security are tied in",
        5: "children, creativity, or planning plays a role",
        6: "health issues, rivalry, or daily work stress appears",
        7: "partnerships and other people are in the picture",
        8: "sudden change, inheritance, or hidden stress is indicated",
        9: "luck, father, travel, or elder siblings connect here",
        10: "career, status, and public life channel the result",
        11: "gains, elder siblings, or income streams are linked",
        12: "distance, expense, foreign life, or withdrawal is suggested",
    }
    return generic.get(lord_h, f"house {lord_h} themes connect")


# (varga, subject house, lord's house) -> human sentence
_LORD_CHANNEL_SPECIFIC: dict[tuple[str, int, int], str] = {
    ("D3", 9, 10): "your elder sibling's job and public image are strongly tied to this house — they may be known through career, and family respect rises or falls with their professional standing",
    ("D3", 11, 4): "your immediate elder co-born is linked to home and mother — they may live near the family base, share in domestic property, or act as the stabiliser at home",
    ("D3", 10, 3): "sibling career results flow through the younger-sibling/courage axis — a co-born may push you into action, or their job involves travel, sales, or technical hands-on work",
    ("D3", 3, 3): "younger sibling theme is doubled — the co-born is prominent, active, and hard to ignore in family decisions",
    ("D1", 11, 6): "elder sibling gains channel through health, service, or rivalry — they may work in medicine, law, military, or competitive fields; their wellbeing affects family mood",
    ("D1", 3, 11): "younger sibling link connects to gains and networks — a younger co-born may actually help your income or friend circle later in life",
    ("D4", 4, 10): "home and mother connect to career — property may come through your job, government, or a parent who worked hard for the house",
    ("D7", 5, 8): "child promise runs through transformation and anxiety — conception may need patience; once born, a child can change the family deeply",
    ("D9", 7, 4): "marriage results flow through home and emotional security — domestic peace is central to partnership quality",
    ("D9", 7, 10): "spouse's career and public standing strongly colour the marriage — respect and status comparisons matter",
    ("D9", 4, 7): "marital happiness links directly to the spouse — partner's behaviour affects home peace daily",
}


def _planet_in_house(varga: str, h: int, planet: str, verdict: str) -> str:
    """One natural sentence for a planet occupying this varga house."""
    key = (varga, h, planet)
    if key in _PLANET_HOUSE_READING:
        return _PLANET_HOUSE_READING[key]
    topic = _short_topic(varga, h)
    fallback = {
        "Sun": f"Sun here puts a spotlight on {topic} — someone in this area wants recognition and can be proud or stubborn.",
        "Moon": f"Moon here makes {topic} emotionally alive — moods, mother-figures, or changing circumstances shape outcomes.",
        "Mars": f"Mars here adds speed, argument, or physical effort to {topic}; injuries or anger flare if the house is stressed.",
        "Mercury": f"Mercury here brings talk, trade, or study into {topic}; a clever or restless person is involved.",
        "Jupiter": f"Jupiter here protects and expands {topic} over time — teachers, elders, or fair guidance help.",
        "Venus": f"Venus here softens {topic} with comfort, art, or affection; relationships ease the area when strong.",
        "Saturn": f"Saturn here delays but steadies {topic}; duty, age, bones, teeth, or chronic fatigue need watching.",
        "Rahu": f"Rahu here makes {topic} unusual — foreign links, sudden ambition, or obsessive focus appear.",
        "Ketu": f"Ketu here thins or spiritualises {topic}; distance, minimalism, or karmic repeat patterns are felt.",
    }
    line = fallback.get(planet, "")
    if verdict == "caution" and line:
        return line + " Because this house is under pressure, these traits show more as strain than blessing."
    return line


_PLANET_HOUSE_READING: dict[tuple[str, int, str], str] = {
    # D3 — younger sibling (3rd)
    ("D3", 3, "Mars"): (
        "Mars sitting on the younger-sibling axis is a classic sign of a bold co-born — likely male or very assertive — "
        "into sports, engineering, police/army, surgery, or property. Your own courage is real; arguments happen but respect can remain."
    ),
    ("D3", 3, "Saturn"): (
        "Saturn here can delay or distance a younger sibling, or give an elder-younger age gap feel — "
        "the co-born may be serious, thin-built, or face joint/skin/chronic fatigue issues."
    ),
    ("D3", 3, "Mercury"): (
        "Mercury here suggests a talkative, clever younger sibling — good with business, accounts, coding, or media; "
        "nervous system and respiratory health need routine care."
    ),
    # D3 — elder sibling luck (9th)
    ("D3", 9, "Sun"): (
        "Sun on the elder-sibling fortune axis means an elder brother/sister is visible in the family — proud, status-conscious, "
        "possibly in government, management, or medicine. Relationship can be warm but ego clashes happen; watch their heart, eyes, and blood pressure in harsh dasha years."
    ),
    ("D3", 9, "Jupiter"): (
        "Jupiter here is supportive for elder siblings — they may do well in teaching, law, finance, or advisory roles and can genuinely bring luck to you."
    ),
    ("D3", 9, "Saturn"): (
        "Saturn here gives a dutiful elder sibling who marries late or carries family burden — helpful but stern; "
        "their bones, teeth, knees, and chronic tiredness need care."
    ),
    # D3 — immediate elder co-born (11th)
    ("D3", 11, "Rahu"): (
        "Rahu on the immediate elder-co-born house often gives an elder sibling on an unconventional path — foreign country, "
        "startup, politics, or sudden rise and fall. Financial help may come in bursts, not steadily; keep expectations realistic."
    ),
    ("D3", 11, "Jupiter"): (
        "Jupiter here is excellent for elder sibling gains — they may earn well, stay ethical, and help you achieve wishes through their network."
    ),
    ("D3", 11, "Saturn"): (
        "Saturn here delays elder sibling's gains but makes them hardworking — they may face job pressure early, then stabilise in government or structured work."
    ),
    # D3 — sibling happiness (4th)
    ("D3", 4, "Jupiter"): (
        "Jupiter in the sibling-happiness house is warm — shared meals, family gatherings, and emotional support among co-born are real, not just polite."
    ),
    # D1 — younger / elder siblings
    ("D1", 3, "Mars"): (
        "Mars in the 3rd gives a younger sibling who is independent and physically active — technical or property-related work suits them; throat and shoulder health are sensitive."
    ),
    ("D1", 11, "Jupiter"): (
        "Jupiter in the 11th supports elder siblings and income — an elder co-born may do well and help you materially or with connections."
    ),
    ("D1", 11, "Saturn"): (
        "Saturn in the 11th can delay gains and strain elder sibling relations — they may face job pressure or health fatigue; you may need to support them before they support you."
    ),
    ("D1", 11, "Mars"): (
        "Mars in the 11th energises elder sibling and income themes — an elder co-born may be competitive, self-employed, or in technical work; gains come through bold networking but arguments over money are possible."
    ),
    ("D1", 11, "Rahu"): (
        "Rahu in the 11th gives sudden gains and unusual elder sibling paths — foreign friends, online income, or an elder co-born who lives far away; verify promises before relying on them financially."
    ),
    # D4 — mother / home
    ("D4", 4, "Moon"): (
        "Moon on the home axis ties mother's emotions directly to property — her mood affects domestic peace; a caring but changeable home atmosphere."
    ),
    ("D4", 4, "Venus"): (
        "Venus here favours a beautiful, comfortable home — vehicles, décor, and mother's grace support property happiness."
    ),
    ("D4", 10, "Mars"): (
        "Mars in the property-career house strongly supports owning built land, house, factory, or workshop — assets come through effort and technical work."
    ),
    # D7 — children
    ("D7", 5, "Ketu"): (
        "Ketu on the children house can delay conception or give a spiritually inclined child — medical timing and dasha periods matter more than worry."
    ),
    ("D7", 5, "Jupiter"): (
        "Jupiter in the 5th is protective for progeny — children tend to be well-guided, educated, and affectionate when other factors agree."
    ),
    ("D7", 5, "Saturn"): (
        "Saturn here delays childbirth but can give responsible parenting — fertility may need patience; first child theme may come after 30."
    ),
    ("D9", 7, "Venus"): (
        "Venus in the navamsha marriage house is excellent — affection, loyalty, and comfort in partnership tend to grow with age, not fade after the wedding."
    ),
    ("D9", 7, "Jupiter"): (
        "Jupiter here protects marriage — spouse may be ethical, educated, or advisory; union carries dharma and fairness."
    ),
    ("D9", 7, "Saturn"): (
        "Saturn here delays marriage or gives an older/dutiful spouse — bond is serious but can feel heavy; knees, bones, and chronic fatigue need care in harsh periods."
    ),
    ("D9", 7, "Rahu"): (
        "Rahu here gives an unconventional union — foreign spouse, inter-caste, or sudden marriage possible; verify character and money calmly."
    ),
    ("D9", 4, "Moon"): (
        "Moon on the marital-happiness axis ties emotions to home — peace after wedding depends on nurturing routines and mother's role in the household."
    ),
    ("D9", 12, "Venus"): (
        "Venus in navamsha 12th is a classical favourable placement — private affection, bed comfort, and pleasure in marriage are supported."
    ),
    ("D9", 1, "Sun"): (
        "Sun on navamsha lagna makes you proud and visible in partnership — leadership in marriage is natural; ego clashes need watching."
    ),
}


def _relation_closer(varga: str, h: int, ev: dict[str, Any]) -> str:
    """Extra plain-language lines for relation-heavy houses (book themes)."""
    verdict = ev.get("verdict", "neutral")
    lord = ev.get("lord", "")
    lord_h = ev.get("lord_house")
    lord_dig = ev.get("lord_dignity", "unknown")
    tenants: list[str] = list(ev.get("tenants") or [])
    lines: list[str] = []

    if varga == "D3" and h == 9:
        lines.append(
            "In plain terms: this is the elder-sibling and luck house — read it for how much support you get from an elder brother/sister, "
            "their education or abroad path, and whether they lift family fortune or need your help."
        )
        if lord == "Venus" and lord_h == 10:
            lines.append(
                "Venus ruling this house but sitting in the career zone suggests your elder sibling may work in finance, design, hospitality, "
                "or a public-facing role — pleasant in person, but relationship can sour if money or status comparisons enter."
            )
        if verdict == "caution":
            lines.append(
                "With this house under stress, expect uneven contact — periods of pride or distance, and times when their job or health (especially digestion, kidneys, or stress-related illness) worries the family."
            )
    elif varga == "D3" and h == 11:
        lines.append(
            "This is the immediate elder co-born house — use it for their income, whether they fulfil promises, and if they connect you to gains or disappoint you."
        )
        if lord == "Jupiter" and lord_h == 4:
            lines.append(
                "The elder sibling lord sitting in the home house often means they stay involved with family property or mother's care — "
                "helpful with domestic decisions even if they live in another city."
            )
        if "Rahu" in tenants:
            lines.append(
                "Rahu here can inflate expectations — the elder sibling may chase big goals abroad or online; verify money and health claims calmly, not through family drama."
            )
    elif varga == "D3" and h == 3:
        lines.append(
            "This is the younger-sibling house — count on it for their personality, courage, job type, and how much they push or support you."
        )
        if "Mars" in tenants and verdict != "caution":
            lines.append(
                "A strong Mars here usually means the younger co-born exists and is physically capable — likely in a hands-on or competitive field; fights are quick but not permanent."
            )
    elif varga == "D3" and h == 6:
        lines.append(
            "Watch this house for sibling illness, debt, office rivalry involving a co-born, or periods when a brother/sister faces job loss."
        )
    elif varga == "D1" and h == 11:
        lines.append(
            "Read this for elder siblings, close friends who act like siblings, and whether wishes fulfil through your network."
        )
    elif varga == "D1" and h == 3:
        lines.append(
            "Read this for younger siblings, your courage, communication style, and short travels — not just 'effort' in abstract terms."
        )
    elif varga == "D4" and h == 4:
        lines.append(
            "This is the heart of home — mother's wellbeing, land, vehicles, and whether you feel emotionally settled where you live."
        )
    elif varga == "D2" and h == 2:
        lines.append(
            "This is your savings and family-wealth pocket — read it for how money is kept, spent on food and speech habits, and whether family helps or drains you."
        )
    elif varga == "D2" and h == 11:
        lines.append(
            "Income streams and gains live here — including whether an elder sibling or network actually puts money in your hand."
        )
    elif varga == "D4" and h == 9:
        lines.append(
            "Fortune in property and relocation — second home, change of city, or father's role in where you settle."
        )
    elif varga == "D7" and h == 1:
        lines.append(
            "Your overall capacity and desire for children — emotional readiness, not only counting births."
        )
    elif varga == "D7" and h == 9:
        lines.append(
            "Grandchildren, fortune through children, and whether kids study or settle far from home."
        )
    elif varga == "D7" and h == 5:
        lines.append(
            "This is the primary children house — number, affection, schooling, and how much joy you derive from progeny."
        )
    elif varga == "D9" and h == 7:
        lines.append(
            "This is the primary marriage house (Bharyamsha) — read it for spouse quality, staying power, and whether the union delivers long-term."
        )
        if verdict == "caution":
            lines.append(
                "Under stress here, watch for delay, separation phases, or partner health/job issues — timing through dasha matters more than fear."
            )
    elif varga == "D9" and h == 4:
        lines.append(
            "Marital happiness and home peace after wedding live here (Sukhamsha) — mother-in-law, domestic comfort, and emotional settling."
        )
    elif varga == "D9" and h == 1:
        lines.append(
            "How you enter marriage as a person — your inner temperament and what you bring into partnership (Lagnamsha)."
        )
    elif varga == "D9" and h == 8:
        lines.append(
            "Mangalya and longevity themes — hidden anxieties, inheritance through marriage, and transformation in the union."
        )
    elif varga == "D9" and h == 12:
        lines.append(
            "Foreign spouse, private life, bed pleasure, and spiritual retreat within marriage — also classical Venus-exaltation zone."
        )

    return " ".join(lines)


# Core prediction stems: (varga, house) -> {positive, neutral, caution}
_STEMS: dict[tuple[str, int], dict[str, str]] = {}

def _stem(varga: str, h: int, pos: str, neu: str, cau: str) -> None:
    _STEMS[(varga, h)] = {"positive": pos, "neutral": neu, "caution": cau}


# ── D1 birth chart ───────────────────────────────────────────────────────
_stem("D1", 1,
      "You carry a strong constitution and people notice your presence. Health and self-confidence generally hold up across life.",
      "Your personality is workable but not effortless — you define yourself through experience rather than instant luck.",
      "Health, confidence, or peace of mind need guarding; do not ignore early warning signs.")
_stem("D1", 2,
      "Money accumulates steadily and family support around finances is real. Your speech and food habits support prosperity.",
      "Income and family wealth are mixed — you can save, but it takes budgeting and clear speech about money.",
      "Financial strain, family friction around money, or speech that creates loss is possible; watch spending and family loans.")
_stem("D1", 3,
      "You likely have younger sibling(s) or close cousins who stay in your life; courage and communication are active strengths.",
      "Younger co-born may exist but the bond is uneven — you communicate when needed rather than constantly.",
      "Younger sibling distance, rivalry, or throat/shoulder health issues are possible; courage may feel blocked at times.")
_stem("D1", 4,
      "Mother's support, home comfort, and property/vehicle prospects are favourable. Education and inner peace are reachable.",
      "Home life is average — you create stability yourself rather than inheriting perfect domestic ease.",
      "Mother's health, property disputes, or emotional unrest at home need attention; moves may be unsettling.")
_stem("D1", 5,
      "Children, creativity, and intelligent pursuits are supported. Speculation can work if you stay disciplined.",
      "Progeny and creative output come with timing — not denied, but not instant.",
      "Delays or stress around children, romance, or speculative money; stomach or liver sensitivity possible.")
_stem("D1", 6,
      "You overcome rivals and health challenges with effort; service jobs and daily discipline can build strength.",
      "Ordinary health ups and downs; debts and competitors exist but are manageable.",
      "Chronic illness, heavy debt, or strong enemies are indicated — prevention and legal clarity matter.")
_stem("D1", 7,
      "Marriage and partnerships are viable; spouse may bring status or practical support. Business deals can work.",
      "Relationship path is mixed — commitment works with maturity, not early rush.",
      "Marriage delay, partner health stress, or partnership losses possible; choose partners carefully.")
_stem("D1", 8,
      "You can survive crises and may gain through inheritance or research-type work. Longevity is workable with care.",
      "Sudden changes happen but are not catastrophic; hidden matters resolve slowly.",
      "Accidents, chronic hidden illness, or inheritance disputes need caution; avoid reckless risk.")
_stem("D1", 9,
      "Father's role, luck, and higher learning favour you. Long journeys and dharma support life direction.",
      "Fortune comes in phases; father may be supportive but not dominant in luck.",
      "Father's health or relationship strain; luck feels blocked until dasha and effort align.")
_stem("D1", 10,
      "Career and public reputation can rise with sustained work. Authority figures may help you.",
      "Profession grows step by step; status is earned rather than gifted.",
      "Career blocks, humiliation at work, or knee/joint issues possible; avoid power struggles.")
_stem("D1", 11,
      "Elder sibling(s) are likely present and can support gains — they may do well in career or income. Wishes fulfil with time.",
      "Elder co-born or close friends bring moderate gains; income streams exist but fluctuate.",
      "Elder sibling distance, their health/job stress, or blocked income/gains — friendships may feel disappointing.")
_stem("D1", 12,
      "Expenses stay controlled; foreign or spiritual retreat can benefit you. Sleep and feet need routine care.",
      "Some spending and foreign/distance themes; moksha interest may grow quietly.",
      "Heavy expenses, hospitalisation themes, or isolation; foreign settlement may come with cost.")

# ── D2 wealth hora ───────────────────────────────────────────────────────
_stem("D2", 1, "Your hora chart supports earning and holding money — you can build wealth with the right channel.",
      "Financial constitution is average; channel (job vs business vs family) must be chosen consciously.",
      "Wealth-building feels uphill; remedies for lagna lord and savings discipline are important.")
_stem("D2", 2, "Savings grow and family contributes to wealth. You speak about money in a way that attracts resources.",
      "Family money helps sometimes; you must actively save rather than rely on inheritance alone.",
      "Money leaks through family, speech, or food/habit excess; bank balance needs strict tracking.")
_stem("D2", 3, "You earn through self-effort, skills, short projects, or communication — side income is possible.",
      "Income from initiative exists but is irregular; courage in asking for pay raises matters.",
      "Financial gain through effort is blocked; siblings or contracts may drain small gains.")
_stem("D2", 4, "Property, vehicles, and comfort from wealth are supported — home-related assets can appreciate.",
      "Property comfort is moderate; vehicles and home upgrades come gradually.",
      "Property investment caution; vehicles or home repairs may consume savings.")
_stem("D2", 5, "Smart investments, teaching, or creative income can work; financial luck from past merit shows.",
      "Speculation is mixed — small calculated risks only.",
      "Gambling, risky trades, or children-related expenses hurt wealth.")
_stem("D2", 6, "You can pay off debts and beat financial rivals; health costs stay manageable.",
      "Debts and medical bills exist but are not overwhelming.",
      "Debt, litigation, or disease drains wealth — avoid co-signing loans.")
_stem("D2", 7, "Money through spouse, business partner, or clients is indicated; shared ventures can profit.",
      "Partners bring some money but terms must be clear in writing.",
      "Partner-related financial loss or delayed payments from contracts.")
_stem("D2", 8, "Sudden money — inheritance, insurance, or research work — can arrive; also sudden expenses possible.",
      "Financial ups and downs; windfalls and shocks balance out.",
      "Hidden losses, tax issues, or blocked inheritance; avoid illegal money routes.")
_stem("D2", 9, "Fortune eases earning; father's guidance or dharma-aligned work pays. Long-distance money links help.",
      "Luck in money is moderate; father's role in finance is neutral.",
      "Fortune blocked; father's health or beliefs may conflict with your earning path.")
_stem("D2", 10, "Career pays well in this hora; status and salary growth are linked. Government or large org income possible.",
      "Career income is steady but not spectacular.",
      "Job loss themes, salary cuts, or reputation hurting income.")
_stem("D2", 11, "Strong gains and multiple income streams; elder sibling may help financially or network you into money.",
      "Gains arrive but irregularly; elder sibling financial role is minor.",
      "Income wishes delayed; elder sibling may need your financial help instead.")
_stem("D2", 12, "Expenses are controlled; charity and foreign spend are manageable.",
      "Moderate outflow; watch subscriptions and hidden fees.",
      "Heavy expenditure, wasteful spending, or money lost abroad/hospital/legal fees.")

# ── D3 drekkana — siblings & karma fruits ────────────────────────────────
_stem("D3", 1,
      "Your overall nature supports siblings in the chart — co-born are likely and you carry strong personal initiative.",
      "Sibling promise is mixed; you may have one close co-born or cousins who play that role.",
      "Chart denies or strains siblings; you may feel alone in effort or carry family karma solo.")
_stem("D3", 2,
      "Family resources and speech among siblings are generally harmonious; shared family money or values help.",
      "Family talk around siblings is neutral — neither especially warm nor bitter.",
      "Arguments over family money or harsh speech among siblings; eating/habit differences create friction.")
_stem("D3", 3,
      "Younger sibling(s) are indicated — likely bold, active, possibly in technical, sports, or property-related work. You have real courage.",
      "Younger co-born may exist but live at distance or contact is occasional; your courage builds slowly.",
      "Younger sibling absence, serious rivalry, or their health/job struggles worry you; your own initiative feels blocked.")
_stem("D3", 4,
      "Happiness with siblings is genuine — shared home memories, emotional support, and peace among co-born.",
      "Sibling happiness is okay but not central; you find peace elsewhere.",
      "Emotional distance from siblings; mother's health or home tension affects sibling bonds.")
_stem("D3", 5,
      "A second younger sibling or close cousin is possible; planning and intellect among siblings is sharp.",
      "Second co-born theme is weak or replaced by close friends as 'siblings'.",
      "Stress around a second sibling, or overthinking creates friction in sibling plans.")
_stem("D3", 6,
      "Sibling rivalry is manageable; health scares among co-born are not dominant.",
      "Minor disputes or health ups and downs among siblings occur but pass.",
      "Sibling illness, debt, or open rivalry; a co-born may face job loss or chronic health issue.")
_stem("D3", 7,
      "Partnerships formed through sibling networks help; desire and social life link to co-born circles.",
      "Love life and siblings stay in separate lanes.",
      "Partner conflicts triggered by sibling interference or jealousy among co-born.")
_stem("D3", 8,
      "Longevity and crisis-handling are fair; major sibling loss themes are not strong.",
      "Occasional scares or transformation periods; siblings may go through a rough patch.",
      "Serious longevity stress, sibling accident/surgery themes, or deep estrangement after crisis.")
_stem("D3", 9,
      "Elder sibling(s) are likely and can be a luck-bringer — they may do well in education, abroad, or dharma-related work. Support from them is real.",
      "Elder co-born exists but luck from them is moderate; relationship is polite rather than deeply supportive.",
      "Elder sibling distance, their health or career struggle, or luck blocked — you may carry family responsibility alone.")
_stem("D3", 10,
      "Your action and career effort pay off; a sibling may also rise in career or public life.",
      "Career karma is steady; siblings' jobs are average.",
      "Career blocks or sibling's job loss/shame affects family; your effort feels unrewarded publicly.")
_stem("D3", 11,
      "Elder sibling gains and fulfils wishes — they may earn well or help you achieve goals. Gains through sibling network.",
      "Elder co-born does moderately; some help with connections but not major wealth.",
      "Elder sibling financial struggle or broken promise; gains through friends/siblings disappoint.")
_stem("D3", 12,
      "Separation from siblings is not permanent; foreign study/work among co-born is possible without full cut-off.",
      "Some distance — siblings live in different cities but bond on occasions.",
      "Clear separation, loss of contact, or sibling settled abroad with thin emotional link; expenses on their account.")

# ── D4 home & property ───────────────────────────────────────────────────
_stem("D4", 1, "You can own property and find genuine contentment; happiness is reachable with effort.",
      "Domestic happiness is average — you build home peace yourself.",
      "Property ownership and inner peace are strained; mother or home needs extra care.")
_stem("D4", 2, "Family money supports home and vehicles; speech at home is generally pleasant.",
      "Family resources for property are moderate.",
      "Family disputes over assets or harsh speech disturbs home comfort.")
_stem("D4", 3, "Courage in property deals; sibling may share in land or help with short moves.",
      "Sibling role in property is minor.",
      "Sibling dispute over property share or failed short move related to home.")
_stem("D4", 4,
      "Mother is supportive; home, land, or vehicles are strongly indicated. Inner peace and education at home are good.",
      "Mother's role is mixed; home stability comes gradually; one property or vehicle is realistic.",
      "Mother's health needs care; property loss, rental instability, or emotional unrest at home.")
_stem("D4", 5, "Joy from home, children playing at home, and pleasure from what you own.",
      "Domestic pleasure is moderate.",
      "Stress through children at home or creative projects draining domestic peace.")
_stem("D4", 6, "Property disputes are manageable; home debts under control.",
      "Some repair bills or neighbour issues.",
      "Legal dispute over land, heavy home loan, or mother's illness draining peace.")
_stem("D4", 7, "Spouse contributes to home/property; joint purchase or partnership in land works.",
      "Spouse role in property is neutral.",
      "Partner blocks property plan or marriage stress disturbs home.")
_stem("D4", 8, "Inheritance of land possible; sudden shift in home but survivable.",
      "Occasional sudden repairs or inheritance delay.",
      "Property shock, inheritance fight, or mother's serious health scare.")
_stem("D4", 9,
      "Fortune in property — second home, father's support, or successful change of city/country for better life.",
      "Relocation or property luck is moderate.",
      "Displacement from birthplace, father's health, or failed foreign/home move.")
_stem("D4", 10,
      "Career supports property — government land, office space, or Mars-type built assets strongly indicated.",
      "Job-linked housing is average.",
      "Career instability hurts property plans; no strong built-asset signature.")
_stem("D4", 11, "Gains from property — elder sibling may share inheritance or help you buy.",
      "Moderate property gains over time.",
      "Elder sibling dispute over property share or gains blocked.")
_stem("D4", 12, "Spend on home is controlled; foreign home or ashram/spiritual retreat possible.",
      "Some expense on home maintenance or travel.",
      "Property loss, heavy spend on home, or living far from birthplace by necessity.")

# ── D7 children ──────────────────────────────────────────────────────────
_stem("D7", 1, "Your chart supports becoming a parent; bond with children can be warm and responsible.",
      "Progeny is possible with timing; parenting style develops through learning.",
      "Desire or capacity for children is strained; emotional preparation and remedies help.")
_stem("D7", 2, "Children bring family wealth continuity; their speech and values align with family.",
      "Children's financial theme is neutral.",
      "Expense on children or speech/health issues in progeny line.")
_stem("D7", 3, "Children may be courageous, active; sibling bond among your children is indicated.",
      "Children's initiative is average.",
      "Children's accidents, sibling rivalry among kids, or communication stress.")
_stem("D7", 4, "Children find happiness and good education; mother-grandmother bond with kids is strong.",
      "Children's emotional security is workable.",
      "Children's schooling stress, mother's health affecting childcare, or home unrest.")
_stem("D7", 5,
      "Children are clearly promised — birth of progeny is supported; parent–child affection can be deep.",
      "Children come with delay or one primary child theme is stronger.",
      "Conception difficulty, miscarriage themes, or strained bond with a child — medical and dasha timing matter.")
_stem("D7", 6, "Children's health rivals and debts are manageable.",
      "Some illness scares but not dominant.",
      "Children's chronic health issues, fertility treatment, or strong 6th-house obstacle to conception.")
_stem("D7", 7, "Children's marriage prospects are good; second-marriage child theme is possible if applicable.",
      "Children's partnerships develop normally.",
      "Children's relationship stress or progeny from second marriage blocked.")
_stem("D7", 8, "Children's longevity is generally protected.",
      "Some health scares in children's 8th-house periods.",
      "Serious anxiety about children's survival, surgery themes, or hidden child health issues.")
_stem("D7", 9, "Grandchildren and fortune through children are supported; children may live abroad or study far.",
      "Grandchildren theme is moderate.",
      "Few grandchildren, children's luck blocked, or distance from children in adulthood.")
_stem("D7", 10, "Children do well in career/public life; you feel proud of their standing.",
      "Children's career is average.",
      "Children's job struggle or reputation issues worry you.")
_stem("D7", 11, "Wishes around children fulfil; children may become financially helpful later.",
      "Moderate fulfilment of progeny wishes.",
      "Disappointment about number or success of children.")
_stem("D7", 12, "Children may study or settle abroad without full emotional cut-off.",
      "Some separation when children grow up.",
      "Strong separation, children in foreign lands with thin contact, or heavy expense on children.")

# ── D9 navamsha — marriage & dharma maturity ──────────────────────────────
_stem("D9", 1,
      "You enter marriage with a clear, confident inner nature; partnership feels like part of your life purpose.",
      "Your partnership style develops with age — you grow into marriage rather than starting fully formed.",
      "Inner resistance, health, or ego issues can delay or strain how you show up in marriage; work on self first.")
_stem("D9", 2,
      "Money, family values, and speech harmonise well in marriage; in-laws and shared resources generally support the union.",
      "Financial and family-speech themes in marriage are workable with clear communication.",
      "Arguments over money, harsh speech, or family interference in the marriage need conscious boundaries.")
_stem("D9", 3,
      "You communicate boldly in partnership; short trips, siblings-in-law, and initiative keep the bond active.",
      "Courage and communication in marriage are average — you speak when needed.",
      "Rivalry, sibling interference, or throat/shoulder stress from marital arguments possible.")
_stem("D9", 4,
      "Marital happiness and home peace are strongly indicated; emotional comfort after wedding is real and lasting.",
      "Home peace after marriage builds gradually; comfort is reachable with effort.",
      "Domestic unrest, mother-in-law tension, or unsettled home after wedding — property or rental instability possible.")
_stem("D9", 5,
      "Romance, affection, and children after marriage are supported; creative joy in the union grows over time.",
      "Romance and children after marriage come with timing; bond deepens in phases.",
      "Stress around romance, conception after marriage, or creative friction between partners.")
_stem("D9", 6,
      "Marital health rivals and daily stress are manageable; you can overcome obstacles together.",
      "Ordinary ups and downs in health and daily friction; not dominant.",
      "Chronic illness, debt, or open rivalry affecting marriage; service/work stress spills into home.")
_stem("D9", 7,
      "Marriage is clearly promised and can be stable; spouse brings support and the partnership has staying power.",
      "Marriage comes with mixed signals — commitment works when both partners mature together.",
      "Marriage delay, separation risk, or partner health/character stress; choose timing and partner carefully.")
_stem("D9", 8,
      "Mangalya and longevity themes are workable; sudden changes in marriage are survivable with care.",
      "Hidden issues or transformation periods in marriage occur but are not catastrophic.",
      "Serious longevity anxiety, inheritance disputes through marriage, or hidden partner health issues.")
_stem("D9", 9,
      "Luck, dharma, and fortune through spouse are supported; partner may be from a different region or higher learning background.",
      "Fortune through marriage is moderate; spiritual growth through union is gradual.",
      "Father-in-law strain, blocked luck through spouse, or religious/cultural mismatch in marriage.")
_stem("D9", 10,
      "Spouse may do well in career; your public image as a couple can rise; partner supports your status.",
      "Spouse's job and your couple-reputation are average.",
      "Spouse job struggle, humiliation linked to marriage, or career conflict between partners.")
_stem("D9", 11,
      "Gains and wishes fulfil through marriage; spouse or in-laws may help income and networks.",
      "Moderate gains through partnership; wishes fulfil slowly.",
      "Broken promises from spouse side, blocked gains through marriage, or friend-circle friction.")
_stem("D9", 12,
      "Foreign spouse or pleasure in private life is possible without destroying the union; spiritual retreat together.",
      "Some expense on marriage or distance themes; bed-pleasure average.",
      "Heavy expense on partner, foreign separation, hospital themes, or isolation in marriage.")


def build_d1_varga_chart(pc: dict) -> dict[str, Any]:
    """Build D1 chart dict matching divisional chart structure for house examination."""
    meta = pc.get("meta", {})
    lagna = meta.get("lagna_sign") or pc.get("lagna", {}).get("sign", "")
    bodies: dict[str, dict[str, Any]] = {}
    for name in GRAHAS:
        pl = pc.get("planets", {}).get(name, {})
        if not pl.get("sign"):
            continue
        bodies[name] = {
            "sign": pl["sign"],
            "house": pl.get("house"),
            "d1_sign": pl["sign"],
        }
    houses: dict[int, dict[str, Any]] = {}
    for h in range(1, 13):
        hs = house_sign(h, lagna)
        lord = SIGN_LORDS[hs]
        tenants = [n for n, b in bodies.items() if b.get("house") == h]
        houses[h] = {"sign": hs, "lord": lord, "tenants": tenants}
    ll = SIGN_LORDS.get(lagna, "")
    ll_pl = bodies.get(ll) or {}
    return {
        "lagna": lagna,
        "lagna_lord": ll,
        "planets": bodies,
        "houses": houses,
        "lagna_lord_d7_house": ll_pl.get("house"),
    }


def human_house_reading(varga: str, h: int, ev: dict[str, Any]) -> str:
    """Natural-language house reading from evaluation dict."""
    verdict = ev.get("verdict", "neutral")
    lord = ev.get("lord", "")
    lord_h = ev.get("lord_house")
    lord_dig = ev.get("lord_dignity", "unknown")
    tenants: list[str] = list(ev.get("tenants") or [])
    sign = ev.get("sign", "")

    stems = _STEMS.get((varga, h), {})
    base = stems.get(verdict) or stems.get("neutral") or f"This area of life shows mixed results in your {varga} chart."

    short_label = house_label(varga, h).split("&")[0].split(",")[0].strip()
    parts = [f"In {varga} house {h} ({short_label}): {base}"]

    # Lord channel — how results flow
    if lord and lord_h:
        channel = _lord_channel(varga, h, lord_h)
        dig = _dig_word(lord_dig)
        parts.append(
            f"The house lord {lord} is {dig} and sits in the {_ordinal(lord_h)} house, so {channel}."
        )

    # Relation context (book themes in plain language)
    closer = _relation_closer(varga, h, ev)
    if closer:
        parts.append(closer)

    # Planets in the house — concrete human notes
    if tenants:
        for p in tenants[:3]:
            touch = _planet_in_house(varga, h, p, verdict)
            if touch:
                parts.append(touch)
    elif lord_h in _TRIK:
        parts.append(
            f"No planet occupies this house, but the lord's placement in the {_ordinal(lord_h)} house "
            "pulls results toward loss, effort, or delay before success."
        )

    # Sign flavour (brief, human)
    sign_hints = {
        "Aries": "quick, direct energy",
        "Taurus": "stability and material focus",
        "Gemini": "communication and dual paths",
        "Cancer": "emotion and home themes",
        "Leo": "pride and visibility",
        "Virgo": "detail, service, and health attention",
        "Libra": "relationships and balance",
        "Scorpio": "intensity and hidden matters",
        "Sagittarius": "travel, teaching, optimism",
        "Capricorn": "duty, delay, government structure",
        "Aquarius": "networks and unconventional paths",
        "Pisces": "compassion, foreign, or spiritual tone",
    }
    if sign in sign_hints:
        parts.append(f"The sign {sign} adds {sign_hints[sign]} to this reading.")

    return " ".join(p for p in parts if p)


def house_label(varga: str, h: int) -> str:
    return HOUSE_LABELS.get((varga, h), f"House {h}")
