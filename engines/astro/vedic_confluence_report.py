#!/usr/bin/env python3
"""
vedic_confluence_report.py — Deterministic Confluence + User Report (NO LLM).

Synthesises all individual lane reports into:
  1. Vedic_Confluence_*.html  — multi-system vote table + domain verdicts
  2. user_report_*.html       — plain-English client hub

Correlation method:
  * Structured signals are harvested from astro_precompute (dates, dasha, maraka,
    RTVD, Yogini, pillar scores) plus short prediction paragraphs from each lane HTML.
  * all-MiniLM-L6-v2 (sentence-transformers) maps every signal to life-domain
    theme anchors and clusters semantically similar claims across systems.
  * Vote confidence follows vedic_confluence_skill.md (7+ = VERY HIGH, etc.).
  * Final prose is synthesized from the clustered lane sentences themselves — generic
    template lines are fallback only when no lane text exists for a domain.

Fully offline after the first model download. No Cursor / no LLM.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import numpy as np
from astro_precompute import get_house_lord, normalize_precomputed, precompute, resolve_precompute
from chart_resolve import add_chart_source_args, chart_kwargs_from_args
from lane_collectors import collect_all_lanes
from client_report_html import (
    client_css,
    confluence_css,
    health_section_html,
    humanize_remedy_html,
    prediction_card,
    remedies_html,
    seven_pillars_html,
    traffic_light_html,
    transition_calendar_html,
)
from report_language import client_prose
from confluence_longevity_lane import build_longevity_context, longevity_signals, classify_ad_risk, health_light_for_risk

BASE_DIR = Path(__file__).resolve().parent

DOMAINS = ("career", "finance", "marriage", "children", "health", "property",
           "travel", "spiritual", "personality", "current")
DOMAIN_HEADLINE = {
    "career": "Peak Professional Chapter of the Decade",
    "finance": "Income and Savings Lift",
    "marriage": "Partnership Warmth Returns",
    "children": "Family & Creative Focus",
    "health": "Protect Your Baseline Now",
    "travel": "Purposeful Travel Opens",
    "spiritual": "Inner Clarity Season",
    "current": "Quiet Recalibration Before the Surge",
    "personality": "Who You Are",
    "property": "Home & Stability",
}
DOMAIN_TITLE = {
    "career": "Career & Profession", "finance": "Finance & Wealth",
    "marriage": "Spouse & Marriage", "children": "Children & Family",
    "health": "Health & Longevity", "property": "Property & Home",
    "travel": "Travel & Foreign Dimension", "spiritual": "Spiritual & Inner Life",
    "personality": "Character & Personality", "current": "Where You Stand Now",
}
CONF_LABEL = [(7, "VERY HIGH"), (5, "HIGH"), (3, "MODERATE"), (2, "LOW"), (1, "SPECULATIVE")]

# Theme anchors for semantic domain assignment (book-backed vocabulary)
THEME_ANCHORS: dict[str, list[str]] = {
    "career": [
        "promotion leadership recognition senior role career peak professional authority",
        "job employment service hard work competitive income from work",
        "communication intellect mercury career house tenth house public standing",
        "specialisation deep expertise quiet consolidation before expansion",
    ],
    "finance": [
        "wealth income savings financial growth money gains prosperity",
        "expenses losses speculative investment caution contract review",
        "second house family wealth jupiter transit wealth support",
    ],
    "marriage": [
        "marriage spouse partnership harmony relationship renewal commitment",
        "seventh house partnership tension domestic stress family speech",
        "venus love comfort home atmosphere spouse support",
    ],
    "children": [
        "children progeny pregnancy fifth house creativity parenting education",
        "second child family expansion creative projects intellectual offspring",
    ],
    "health": [
        "health illness disease preventive care maraka mrityu bhaga medical watch",
        "fatigue dental eye chronic stress recovery resilience sixth house immunity",
        "digestive metabolic nervous system longevity life risk",
    ],
    "property": [
        "property home real estate fourth house domestic upgrade relocation",
        "vehicle conveyance home purchase land",
    ],
    "travel": [
        "foreign travel international assignment abroad relocation long journey",
        "ninth house dharma pilgrimage foreign links global career",
    ],
    "spiritual": [
        "spiritual meditation introspection ketu detachment inner growth dharma meaning",
        "philosophy study belief system soul purpose",
    ],
    "personality": [
        "intellect communication adaptability gemini lagna mercury mind analytical",
        "charm venus aesthetics emotional moon home rhythm competitive mars gains",
        "identity self expression pillar strength character",
    ],
    "current": [
        "right now current period transition pause prepare upcoming shift",
        "present window recalibration between career cycles consolidation",
    ],
}

# Affirmative book-backed prediction lines (semantically selected per cluster)
BOOK_LINES: dict[str, dict[str, list[str]]] = {
    "career": {
        "positive": [
            "Your professional standing is entering its strongest chapter of the decade — this is the window to claim a senior role, lead a flagship project, or accept the recognition you have earned.",
            "Career advancement now comes through disciplined delivery and visible expertise; the sky supports bold professional moves backed by proof, not hype.",
            "Leadership and public credit consolidate in this period — put your name on work that outlasts the quarter.",
        ],
        "caution": [
            "Career progress continues but demands patience — consolidate skills now so the next expansion phase meets you prepared, not exhausted.",
            "Avoid chasing visibility for its own sake; depth and finish quality matter more than noise in this quieter band.",
        ],
        "neutral": [
            "Work life steadies into a maintenance rhythm — honour commitments, refine systems, and keep your network warm for the lift ahead.",
        ],
    },
    "finance": {
        "positive": [
            "Income and savings capacity improve meaningfully — money conversations flow more easily when you act on structured plans rather than impulse.",
            "Wealth support strengthens from mid-2026 onward; this is an excellent time to renegotiate compensation, formalise bonuses, or strengthen family financial morale.",
            "Gains arrive through earned effort and quality deals — favour contracts you can defend line by line.",
        ],
        "caution": [
            "Read every financial document twice before signing — ambition can outpace risk controls in this band.",
            "Keep speculative bets small; consolidation beats lottery thinking until the peak window opens.",
        ],
        "neutral": ["Finances hold steady with careful stewardship — no dramatic windfall, no collapse."],
    },
    "marriage": {
        "positive": [
            "Partnership warmth and domestic ease improve — invest in closeness now and the relationship rewards you with stability through busier years ahead.",
            "This is a renewal window for committed bonds: honesty, small rituals, and shared plans matter more than grand gestures.",
        ],
        "caution": [
            "Household tone needs deliberate care — clear agreements prevent slow-burn friction when career demands rise.",
            "A sensitive domestic band approaches later in the decade; kindness and preventive communication are your best insurance.",
        ],
        "neutral": ["Partnership quality reflects daily habits more than cosmic mood — keep showing up."],
    },
    "children": {
        "positive": [
            "Children, creativity, or passion-projects take centre stage — favour one meaningful commitment over scattered starts.",
            "If family expansion is on your mind, the coming Venus-rich windows offer the cleanest astrological support.",
        ],
        "caution": [
            "Parenting and creative energy call for editing rather than expansion — finish what is open before adding new obligations.",
        ],
        "neutral": ["Family themes run in the background unless you choose to activate them."],
    },
    "health": {
        "positive": [
            "Your chart carries real recovery strength — consistent routines now build a buffer that pays off in demanding years ahead.",
            "Preventive care is your advantage; small habits today prevent loud alarms tomorrow.",
        ],
        "caution": [
            "Schedule a thorough health review before the late-2030 window — this is prudence, not fear.",
            "Watch sleep, digestion, and stress load through the mid-40s; your body rewards maintenance over heroics.",
        ],
        "neutral": ["Baseline health is workable — stay consistent, not complacent."],
    },
    "property": {
        "positive": [
            "Domestic stability and home comfort improve — smaller upgrades and family-centred spending beat major purchases for now.",
        ],
        "caution": ["Major property moves lack strong multi-system backing in the near term — plan, don't rush."],
        "neutral": ["Home life is stable; big real-estate decisions can wait for a clearer collective signal."],
    },
    "travel": {
        "positive": [
            "Purposeful travel and international links open — especially when tied to work, learning, or expertise sharing.",
            "Foreign-facing opportunities strengthen in the late 2020s; prepare credentials and networks now.",
        ],
        "caution": ["Verify visas, contracts, and itineraries carefully — travel is favoured but details matter."],
        "neutral": ["Short journeys and learning trips flow well; grand relocation is optional, not required."],
    },
    "spiritual": {
        "positive": [
            "This is a receptive season for inner work — meditation, study, or ethical recommitment lands deeper than usual.",
            "Release ego-driven projects that no longer fit; clarity returns when you make space for it.",
        ],
        "neutral": ["Spiritual life deepens quietly — no drama required, only honest attention."],
    },
    "personality": {
        "positive": [
            "You are built for intellect-led achievement with genuine social grace — lead with craft, not performance.",
            "Competitive income drive and analytical depth are core gifts; aim them at measurable wins.",
        ],
        "neutral": ["Your nature blends adaptability with disciplined effort — consistency is the superpower."],
    },
    "current": {
        "positive": [
            "You are in a transition band between louder chapters — edit the portfolio, deepen skill, and prepare for the next expansion phase named in your dasha table.",
            "Multiple clocks agree: slow down now, then act decisively when the favourable sub-period opens.",
        ],
        "caution": ["Do not force major leaps in the next few months — preparation beats pressure."],
        "neutral": ["A transition quarter: quieter outwardly, fertile inwardly."],
    },
}

# Affirmative character lines — semantically matched to personality cluster
NATURE_TRAITS: list[tuple[str, str, str]] = [
    ("★", "Work is the headline of your story. The combined picture keeps returning to public role, craft, and the quality of what you put your name on. You are built to think, communicate, and refine output until it survives scrutiny.", "career"),
    ("●", "Grace and rigour share the same desk. Charm, aesthetics, and people skills are genuine assets; the counterweight is clean paperwork, clear scopes, and deadlines that do not rely on last-minute heroics.", "personality"),
    ("▶", "Home rhythm feeds performance. When domestic schedules wobble, your focus fractures faster than peers notice. Stable meals, sleep, and a calm physical base are performance equipment, not luxuries.", "marriage"),
    ("◆", "Income likes effortful networks. Gains show up through teams, targets, and competitive arenas more than through passive luck. The same signature rewards saying no to empty hustle and yes to measurable wins.", "finance"),
    ("♠", "Partnership is a long lesson, not a one-night rewrite. Contracts in love and business need early honesty because slow-burn trust tests arrive when shortcuts were taken.", "marriage"),
    ("✦", "Hidden strength: recovery after overload. Your chart gives an unusually strong fight-back zone for illness and workplace stress — the body rewards maintenance, not panic.", "health"),
    ("◇", "You need thinking time before you sign, then visible leadership once you commit. Initiating energy and introspective depth share the same life — neither cancels the other.", "personality"),
    ("→", "Your career is carved in chapters rather than one lottery ticket. Recognition grows when each chapter has a flagship piece people can cite.", "career"),
]

HOUSE_PAST: dict[int, str] = {
    1: "identity and how the world first read you",
    2: "family speech, savings habits, and early material lessons",
    3: "siblings, courage, short journeys, and skill experiments",
    4: "home base, mother-linked routines, and emotional security",
    5: "schooling, creativity, and measuring yourself against peers",
    6: "discipline, health habits, and competitive comparison",
    7: "partnerships and learning fairness in one-to-one bonds",
    8: "joint resources, hidden work, and deep self-transformation",
    9: "travel, belief systems, and stretching beyond birthplace comfort",
    10: "public role, career visibility, and the quality of your craft",
    11: "peer networks, income experiments, and alliance-building",
    12: "retreat, foreign links, and inner processing away from noise",
}

MD_PAST_BODY: dict[str, str] = {
    "Moon": "Memory, home rhythm, and how feelings were handled in the household shaped the baseline. Material lessons landed early because emotional security and family speech were wired together.",
    "Mars": "Competition, courage, and proving yourself against standards took centre stage. Physical outlets and hard work likely mattered as a pressure valve when life felt tight.",
    "Rahu": "Ambitious network-building dominated — peer circles beyond birthplace comfort, income experiments, and a visible push toward career crystallisation.",
    "Jupiter": "Joint resources, authority expectations, and reputation transformation moved to the foreground. Contracts, deliverables, and leadership tests arrived under expansion tones.",
    "Saturn": "Duty-heavy years demanded patience and structure. Progress came through sustained effort rather than quick wins — the cosmic gears slowed to test endurance.",
    "Mercury": "Communication, contracts, and intellect-led work led the story. Documents, learning, and refining how you expressed ideas mattered more than raw visibility.",
    "Ketu": "A stripping-back chapter — releasing outdated projects, inner recalibration, and stepping back from ego-driven noise to see what still deserved energy.",
    "Venus": "Comfort, partnership warmth, and creative or family themes rose. Quality of life, aesthetics, and relational ease competed with career noise for attention.",
    "Sun": "Visibility and authority moved forward — public role, recognition, and stepping into a clearer professional identity.",
}

LORD_REMEDY: dict[str, tuple[str, str]] = {
    "Sun": ("Sunday discipline", "Om Suryaya Namah at sunrise; let visible leadership rest on steady habits, not performance."),
    "Moon": ("Monday household rhythm", "Om Chandrayaya Namah; protect sleep and calm speech — mood and focus move together in your map."),
    "Mars": ("Tuesday physical outlet", "Om Mangalaya Namah; channel heat into exercise and measurable targets, not arguments."),
    "Mercury": ("Wednesday craft blocks", "Om Budhaya Namah; green foods; finish documents and learning before chasing the next role."),
    "Jupiter": ("Thursday structured growth", "Om Gurave Namaha; read every clause; favour earned income over speculative bets."),
    "Venus": ("Friday partnership warmth", "Om Shukraya Namah; small rituals, aesthetics, and honest money talks beat grand gestures."),
    "Saturn": ("Saturday proof stacks", "Om Sham Shanicharaya Namah; patience and structure — promotions arrive through endurance, not surprise leaps."),
    "Rahu": ("Ambition with paperwork", "Ground network ambition; verify every verbal promise in writing before you commit."),
    "Ketu": ("Dawn quiet minutes", "Five still minutes before the phone; release one ego project that no longer earns its place."),
}

# Question → life domain (keyword pass, same family as horary_precompute.detect_topic)
QUESTION_KEYWORDS: dict[str, list[str]] = {
    "children": ["child", "children", "baby", "son", "daughter", "pregnant", "birth", "progeny", "fertility"],
    "marriage": ["marriage", "marry", "wedding", "husband", "wife", "partner", "spouse", "relationship", "divorce", "love"],
    "career": ["job", "career", "promotion", "salary", "business", "work", "employment", "interview", "profession", "role", "startup"],
    "health": ["health", "disease", "illness", "sick", "hospital", "surgery", "recover", "medical", "pain", "cancer"],
    "finance": ["money", "finance", "loan", "wealth", "investment", "debt", "income", "savings", "bonus"],
    "property": ["property", "house", "home", "land", "real estate", "flat", "apartment", "vehicle", "car"],
    "travel": ["travel", "trip", "foreign", "abroad", "visa", "relocation", "move", "journey", "immigration"],
    "spiritual": ["spiritual", "meditation", "purpose", "dharma", "meaning", "faith", "karma"],
}

HORARY_TOPIC_TO_DOMAIN = {
    "children": "children", "marriage": "marriage", "career": "career", "job": "career",
    "health": "health", "disease": "health", "finance": "finance", "travel": "travel",
    "education": "career", "litigation": "health", "loan": "finance", "property": "property",
    "general": None,
}

# Domain-specific remedies when focus question targets that area (book-backed, plain English)
DOMAIN_FOCUS_REMEDIES: dict[str, list[tuple[str, str]]] = {
    "career": [
        ("Lagna lord — professional edge", "{ll_remedy}"),
        ("Peak-window discipline ({peak_window})", "Schedule visible launches inside your strongest career sub-period; negotiate compensation in writing; bank recovery days between high-visibility weeks."),
    ],
    "finance": [
        ("Wealth karaka — structured gains", "{jup_remedy}"),
        ("Contract hygiene ({peak_window})", "Keep three folders — tax, insurance, employment — updated quarterly during favourable income sub-periods."),
    ],
    "marriage": [
        ("Seventh-house partnership", "{ven_remedy}"),
        ("Household speech ({h7_lord})", "Calm weekly check-ins; transparency on money and health before duty-heavy sub-periods arrive."),
    ],
    "children": [
        ("Fifth-house creativity", "Finish open creative commitments before starting new ones; one meaningful parenting or passion-project focus at a time."),
        ("Jupiter — progeny support", "{jup_remedy}"),
    ],
    "health": [
        ("Preventive core ({health_window})", "Annual labs before maraka-sensitive sub-periods; Maha-Mrtyunjaya mantra daily; sleep window protected five nights weekly."),
        ("Body maintenance", "Strength training twice weekly; high-fibre meals; hard stops on all-nighters when load rises."),
    ],
    "travel": [
        ("Ninth-house purpose ({travel_window})", "Prepare credentials and networks before foreign-facing sub-periods; verify visas and contracts line by line."),
        ("Mercury travel support", "Double-check tickets and itineraries; favour work-linked or study-linked journeys over random noise."),
    ],
    "property": [
        ("Fourth-house stability", "Smaller domestic upgrades beat rushed major purchases; legal review is sacred if a big deed move is unavoidable."),
        ("Mars property prudence", "Slow contracts; clear equity; no impulse land or vehicle bets in mixed-signal years."),
    ],
    "spiritual": [
        ("Ketu inner work", "Five quiet minutes before phone each dawn; release one ego project that no longer fits."),
        ("Saturn discipline", "One ethical rule you will not break for money — write it where you see it weekly."),
    ],
}

LANE_FILES = {
    "Pillar": "Vedic_Pillar_{slug}_*.html",
    "Vimshottari": "Vedic_Vimshottari_{slug}_*.html",
    "BNN": "Vedic_BNN_{slug}_*.html",
    "KP": "Vedic_KP_{slug}_*.html",
    "Jaimini": "Vedic_Jaimini_{slug}_*.html",
    "Yogini": "Vedic_Yogini_{slug}_*.html",
    "Ashtakavarga": "Vedic_Ashtakavarga_{slug}_*.html",
    "RTVD": "Vedic_RTVD_{slug}_*.html",
    "Longevity": "Vedic_Longevity_{slug}_*.html",
    "BlindChart": "Vedic_BlindChart_{slug}_*.html",
    "Numerology": "Numerology_{slug}_*.html",
    "Bhardwaj": "Vedic_Bhardwaj_{slug}_*.html",
}

# Lanes that supply structured claims via lane_collectors — HTML scrape is fallback only.
COLLECTOR_LANES = frozenset({"BNN", "KP", "Mehta", "Jaimini", "Bhardwaj", "KVS", "Goel", "Longevity", "Ashtakavarga"})

HTML_SECTION_DOMAIN = (
    (re.compile(r"career|profession|10th|job|work", re.I), "career"),
    (re.compile(r"wealth|finance|income|money|2nd|11th", re.I), "finance"),
    (re.compile(r"marriage|spouse|partner|7th|relationship", re.I), "marriage"),
    (re.compile(r"child|progeny|5th|creativ", re.I), "children"),
    (re.compile(r"education|school|learning|study", re.I), "children"),
    (re.compile(r"health|longevity|6th|disease|vitality", re.I), "health"),
    (re.compile(r"property|home|4th|land|house", re.I), "property"),
    (re.compile(r"travel|foreign|9th|abroad", re.I), "travel"),
    (re.compile(r"spiritual|moksha|inner|dharma", re.I), "spiritual"),
    (re.compile(r"personality|character|lagna|temperament", re.I), "personality"),
    (re.compile(r"right now|current|present", re.I), "current"),
    (re.compile(r"methodology|core rules|book-backed", re.I), "unknown"),
)

HTML_SKIP = re.compile(
    r"\b(table|checkbox|font-family|margin|padding|stylesheet|deterministic rule|"
    r"educational purpose|methodology|ocr corpus|step \d|reference only|"
    r"cancellation of debility often ignored|rules\d|book ocr|"
    r"ashtakavarga scores how many|eight cosmic factors|never judge a house solely|"
    r"seven cara karakas rank soul roles|if the 6th cusp sub lord signifies|"
    r"bnn:\s*4th house = foundational|use sav for structural)\b",
    re.I,
)

METHODOLOGY_TEXT = re.compile(
    r"ashtakavarga scores how many|eight cosmic factors approve|"
    r"never judge a house solely by sav|seven cara karakas rank soul roles|"
    r"if the 6th cusp sub lord signifies houses 6, 8|"
    r"mahadasha lord.{0,12}bav qualifies|bnn:\s*4th house = foundational|"
    r"use sav for structural house strength|bindus a planet collects|"
    r"educational purpose only|metaphorical only|symbolic colour, not literal",
    re.I,
)

EDUCATION_TEXT = re.compile(
    r"fields of study|educational interest|foundational schooling|higher learning|"
    r"primary \(4th|intelligence \(5th lord\)|academic skill",
    re.I,
)

FAMILY_BLEED = re.compile(
    r"\b(father|mother|wife|husband|brother|sister)\b|"
    r"land or property|real estate|property gains|your wife is",
    re.I,
)

CONF_RANK = {"SPECULATIVE": 0, "LOW": 1, "MODERATE": 2, "HIGH": 3, "VERY HIGH": 4}
MIN_LANES_FOR_MODERATE = 8
MIN_LANES_FOR_HIGH = 6
CORE_LANE_COUNT = len(LANE_FILES)


@dataclass
class Signal:
    system: str
    domain: str
    direction: str  # positive | caution | neutral
    timing: str
    text: str


@dataclass
class Cluster:
    domain: str
    direction: str
    timing: str
    systems: list[str] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)
    affirmation: str = ""
    confidence: str = "SPECULATIVE"
    score: float = 0.0


def _e(s) -> str:
    return html.escape(str(s))


def _strip_html(raw: str) -> str:
    raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = re.sub(r"\s+", " ", raw)
    return raw.strip()


def _parse_date_short(iso: str) -> str:
    try:
        d = datetime.strptime(iso[:10], "%Y-%m-%d").date()
        return d.strftime("%b %Y")
    except ValueError:
        return iso[:7] if iso else ""


def _conf_label(n: int) -> str:
    for thresh, label in CONF_LABEL:
        if n >= thresh:
            return label
    return "SPECULATIVE"


def _count_lane_files(reports_dir: Path, slug: str) -> int:
    n = 0
    for pat in LANE_FILES.values():
        if _glob_lane(reports_dir, pat.format(slug=slug)):
            n += 1
    return n


def _cap_confidence(label: str, lane_count: int, *, speculative: bool = False) -> str:
    """Cap confidence when lane HTML is missing or affirmation used generic fallback."""
    if speculative:
        return "SPECULATIVE"
    norm = str(label).upper().replace("-", " ")
    rank = CONF_RANK["MODERATE"]
    for name in ("VERY HIGH", "HIGH", "MODERATE", "LOW", "SPECULATIVE"):
        if name in norm:
            rank = CONF_RANK[name]
            break
    if lane_count < 4:
        rank = min(rank, CONF_RANK["LOW"])
    elif lane_count < MIN_LANES_FOR_MODERATE:
        rank = min(rank, CONF_RANK["MODERATE"])
    elif lane_count < MIN_LANES_FOR_HIGH:
        rank = min(rank, CONF_RANK["HIGH"])
    for name, r in sorted(CONF_RANK.items(), key=lambda x: -x[1]):
        if rank >= r:
            return name
    return "SPECULATIVE"


def _is_speculative_affirmation(text: str) -> bool:
    return text.strip().startswith("[SPECULATIVE")


def _parse_dob(dob: str) -> Optional[date]:
    try:
        return datetime.strptime(dob[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _age_at(dob: date, when: date) -> int:
    return max(0, (when - dob).days // 365)


def _lord_past_clause(planets: dict, lord: str) -> str:
    pl = planets.get(lord, {})
    house = pl.get("house", 0)
    dig = pl.get("dignity", "")
    theme = HOUSE_PAST.get(house, "experience and growth")
    if dig in ("exalted", "own_sign", "moolatrikona"):
        strength = "with solid underlying support"
    elif dig == "debilitated":
        strength = "with real friction that demanded extra proof — nothing was handed freely"
    else:
        strength = "in a mixed, workaday tone"
    return f"In your chart this routes through the {house}th-house life area ({theme}) {strength}."


def _build_past_chapters(pc: dict) -> list[tuple[str, str]]:
    """Chart-specific past reconstruction from Vimshottari MD/AD + Moon placement."""
    meta = pc["meta"]
    dob = _parse_dob(meta["dob"])
    if not dob:
        return []
    planets = pc["planets"]
    vim = pc["vimshottari"]
    today = date.today()
    chapters: list[tuple[str, str]] = []

    moon = planets.get("Moon", {})
    moon_h = moon.get("house", 4)
    first_md = (vim.get("sequence") or [None])[0]
    if first_md:
        end0 = datetime.strptime(first_md["end"][:10], "%Y-%m-%d").date()
        a1 = _age_at(dob, end0)
        body = MD_PAST_BODY.get(first_md["md_lord"], "Formation and early conditioning set the emotional baseline.")
        chapters.append((
            f"Ages 0–{min(a1, 12)} · {first_md['md_lord']} childhood chapter",
            f"{body} {_lord_past_clause(planets, first_md['md_lord'])} Moon sits in the {moon_h}th house — home and memory themes are especially vivid in this map.",
        ))

    for md in vim.get("sequence") or []:
        if md.get("status") != "past":
            continue
        lord = md["md_lord"]
        start_d = datetime.strptime(md["start"][:10], "%Y-%m-%d").date()
        end_d = datetime.strptime(md["end"][:10], "%Y-%m-%d").date()
        if _age_at(dob, end_d) <= 12:
            continue  # already covered by childhood card
        lbl = (f"{_parse_date_short(md['start'])} – {_parse_date_short(md['end'])} · "
               f"{lord} mahadasha (ages {_age_at(dob, start_d)}–{_age_at(dob, end_d)})")
        body = MD_PAST_BODY.get(lord, f"The {lord} mahadasha coloured this stretch of life.")
        chapters.append((lbl, f"{body} {_lord_past_clause(planets, lord)}"))

    past_ads = [a for a in vim.get("current_md_antardashas", []) if a.get("status") == "past"]
    for ad in past_ads[-2:]:
        lord = ad["ad_lord"]
        rng = f"{_parse_date_short(ad['start'])} – {_parse_date_short(ad['end'])}"
        md_lord = vim.get("current_md", {}).get("md_lord", "")
        lbl = f"{rng} · {md_lord}–{lord} sub-period"
        body = MD_PAST_BODY.get(lord, f"The {lord} sub-period closed a recent band of experience.")
        chapters.append((lbl, f"{body} {_lord_past_clause(planets, lord)}"))

    cur_ad = next((a for a in vim.get("current_md_antardashas", []) if a.get("status") == "current"), None)
    if cur_ad:
        lord = cur_ad["ad_lord"]
        rng = f"{_parse_date_short(cur_ad['start'])} – {_parse_date_short(cur_ad['end'])}"
        md_lord = vim.get("current_md", {}).get("md_lord", "")
        lbl = f"Now · {md_lord}–{lord} sub-period ({rng})"
        if lord == "Ketu":
            tone = "You are in a quiet recalibration band — edit the portfolio, deepen skill, and release what no longer earns its place."
        elif lord == "Venus":
            tone = "Partnership warmth, income lift, and visible professional polish are the headline — claim recognition you have earned."
        elif lord == "Mercury":
            tone = "Communication, contracts, and intellect-led delivery dominate — finish what is open before adding new obligations."
        elif lord == "Saturn":
            tone = "Structure, duty, and slower gears — promotions and accountability arrive through proof stacks, not surprise leaps."
        else:
            tone = MD_PAST_BODY.get(lord, f"The {lord} sub-period sets the present tone.")
        chapters.append((lbl, f"{tone} {_lord_past_clause(planets, lord)}"))

    return chapters[:6]


AD_DOMAIN_LIGHTS: dict[str, tuple[str, tuple[str, ...]]] = {
    "Ketu": ("Transition — quiet career; inner work and skill depth. Prepare for the next expansion sub-period.", ("🟡", "🟡", "🟢", "🟢", "🟢")),
    "Venus": ("Peak warmth — career recognition, income lift, and partnership ease can run together.", ("🟢", "🟢", "🟡", "🟢", "🟢")),
    "Sun": ("Visibility chapter — authority and expert recognition; steady health maintenance.", ("🟡", "🟡", "🟢", "🟡", "🟢")),
    "Moon": ("Home rhythm and emotional pacing — protect sleep and digestion; routines beat heroic overwork.", ("🟡", "🟡", "🟢", "🟡", "🟢")),
    "Mars": ("High-drive window — channel energy into discipline; pace competition and body heat.", ("🟡", "🟡", "🟡", "🟡", "🟡")),
    "Rahu": ("Ambitious opportunity — network expansion with paperwork; do not sacrifice rest for ambition.", ("🟢", "🟡", "🟡", "🟡", "🟡")),
    "Jupiter": ("Expansion tone — learning, authority, and joint resources move forward with proof stacks.", ("🟢", "🟢", "🟢", "🟢", "🟢")),
    "Saturn": ("Duty-heavy years — patience, structure, and sustained effort beat quick wins.", ("🟡", "🟡", "🟡", "🟡", "🟡")),
    "Mercury": ("Contracts and craft — communication, documents, and intellect-led delivery lead.", ("🟢", "🟢", "🟡", "🟡", "🟢")),
}
def _ad_lights(pc: dict, ad: dict) -> tuple[str, tuple[str, ...]]:
    """Theme + traffic lights; health column uses book OCR maraka risk tier."""
    lord = ad["ad_lord"]
    theme, lights = AD_DOMAIN_LIGHTS.get(
        lord, (f"{lord} sub-period — mixed themes; stay deliberate.", ("🟡",) * 5),
    )
    lights = list(lights)
    _cls, _mb, risk, risk_theme = classify_ad_risk(pc, lord)
    lights[2] = health_light_for_risk(risk)
    if risk in ("High", "Highest"):
        theme = risk_theme
    return theme, tuple(lights)


AD_YEAR_SIGNAL: dict[str, str] = {
    "Venus": "G", "Jupiter": "G", "Mercury": "G", "Sun": "A",
    "Ketu": "A", "Saturn": "A", "Moon": "A", "Mars": "R", "Rahu": "A",
}

DIG_PHRASE = {
    "exalted": "with rare underlying strength",
    "own_sign": "with solid native support",
    "moolatrikona": "with focused operational strength",
    "debilitated": "through friction that demands extra proof",
    "neutral_sign": "in a steady, workaday rhythm",
}


def _ad_at_date(pc: dict, when: date) -> tuple[str, dict | None]:
    vim = pc.get("vimshottari", {})
    md_lord = vim.get("current_md", {}).get("md_lord", "")
    for ad in vim.get("current_md_antardashas", []):
        try:
            start = datetime.strptime(ad["start"][:10], "%Y-%m-%d").date()
            end = datetime.strptime(ad["end"][:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        if start <= when <= end:
            return md_lord, ad
    return md_lord, None


def _ad_window(ad: dict) -> str:
    return f"{_parse_date_short(ad.get('start', ''))} – {_parse_date_short(ad.get('end', ''))}"


def _future_ads(pc: dict, *, include_current: bool = True) -> list[dict]:
    statuses = ("current", "future") if include_current else ("future",)
    return [a for a in pc.get("vimshottari", {}).get("current_md_antardashas", []) if a.get("status") in statuses]


def _peak_career_window(pc: dict) -> str | None:
    maraka = {
        pc.get("longevity", {}).get("maraka_1", {}).get("lord"),
        pc.get("longevity", {}).get("maraka_2", {}).get("lord"),
    }
    best: tuple[int, str] | None = None
    for ad in _future_ads(pc):
        lord = ad["ad_lord"]
        pl = pc.get("planets", {}).get(lord, {})
        house = pl.get("house", 0)
        dig = pl.get("dignity", "")
        score = 0
        if lord == "Venus":
            score += 4
        if house in (10, 11):
            score += 3
        if dig in ("exalted", "own_sign", "moolatrikona"):
            score += 2
        if lord in maraka:
            score -= 3
        if lord in ("Ketu", "Saturn") and house in (6, 8, 12):
            score -= 1
        if best is None or score > best[0]:
            best = (score, _ad_window(ad))
    return best[1] if best and best[0] > 0 else None


def _health_watch_windows(pc: dict) -> list[str]:
    return build_longevity_context(pc).health_watch_windows


def _travel_window(pc: dict) -> str | None:
    for ad in _future_ads(pc):
        lord = ad["ad_lord"]
        pl = pc.get("planets", {}).get(lord, {})
        if pl.get("house") in (9, 12) or lord in ("Jupiter", "Rahu"):
            return _ad_window(ad)
    return _peak_career_window(pc)


def _remedy_context(pc: dict) -> dict[str, str]:
    ll = pc["meta"]["lagna_lord"]
    ll_title, ll_body = LORD_REMEDY.get(ll, (f"{ll} strength", f"Strengthen {ll} through consistent weekly discipline."))
    jup_title, jup_body = LORD_REMEDY.get("Jupiter", ("Jupiter support", "Thursday gratitude and structured growth."))
    ven_title, ven_body = LORD_REMEDY.get("Venus", ("Venus warmth", "Friday partnership ritual and relational ease."))
    peak = _peak_career_window(pc) or "your next favourable sub-period"
    health = _health_watch_windows(pc)
    health_w = health[0] if health else peak
    travel = _travel_window(pc) or peak
    h7 = pc.get("house_lords", {}).get(7, {}).get("lord", "Venus")
    return {
        "ll_remedy": f"{ll_title}: {ll_body}",
        "jup_remedy": f"{jup_title}: {jup_body}",
        "ven_remedy": f"{ven_title}: {ven_body}",
        "peak_window": peak,
        "health_window": health_w,
        "travel_window": travel,
        "h7_lord": h7,
    }


def _fill_remedy_templates(blocks: list[tuple[str, str]], ctx: dict[str, str]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for title, body in blocks:
        t = title.format(**ctx)
        b = body.format(**ctx)
        out.append((t, b))
    return out


def _gemstone_and_remedy_html(
    pc: dict,
    *,
    question: str = "",
    domain: str = "",
    include_psych: bool = True,
) -> str:
    """Chart-based gemstones (rules40/41) plus optional behavioural remedy lines."""
    gem_html = ""
    try:
        from gemstone_remedy import build_remedy_report, render_remedy_section_html
        gem_report = build_remedy_report(pc, question=question, domain=domain)
        gem_html = humanize_remedy_html(render_remedy_section_html(gem_report, compact=False))
    except Exception:
        gem_html = ""
    psych_html = ""
    if include_psych:
        psych_html = "".join(
            f'<div class="remedy-box"><h4>{_e(title)} (behaviour)</h4><p>{_e(body)}</p></div>'
            for title, body in _build_remedy_blocks(pc)[:2]
        )
    if not gem_html and not psych_html:
        return "<p>Nothing special is needed here — the basics carry you a long way: good sleep, a clear head, and honest paperwork.</p>"
    psych_block = ""
    if psych_html:
        psych_block = f'<div class="remedy-psych" style="margin-top:16px">{psych_html}</div>'
    return f"{gem_html}{psych_block}"


def _build_remedy_blocks(pc: dict) -> list[tuple[str, str]]:
    ctx = _remedy_context(pc)
    ll = pc["meta"]["lagna_lord"]
    ll_title, ll_body = LORD_REMEDY.get(ll, (f"{ll} strength", f"Strengthen {ll} through consistent weekly discipline."))
    blocks: list[tuple[str, str]] = [
        (f"{ll_title} (ongoing)", ll_body),
    ]
    health = _health_watch_windows(pc)
    if health:
        blocks.append((
            f"Stay ahead of your health ({health[0]})",
            "Book a yearly check-up — especially before the gentler health seasons noted above. Look after digestion, keep moving, drink enough water, and guard your sleep when life gets busy. This is simple prudence, not something to worry about.",
        ))
    peak = _peak_career_window(pc)
    if peak:
        blocks.append((
            f"Make the most of your best window ({peak})",
            "When work and recognition are flowing, pour a little of that energy back into the people you love and your own wellbeing too. Regular time together, honest money talks, and writing down what you agree to will carry you far.",
        ))
    blocks.append((
        "Tend your closest relationship",
        "Small, steady attention beats grand gestures. A weekly check-in, transparency about money and health, and a little patience keep your most important bond strong through the busy years.",
    ))
    return blocks[:4]


def _ad_year_theme(pc: dict, md_lord: str, ad: dict) -> tuple[str, str]:
    lord = ad["ad_lord"]
    pl = pc.get("planets", {}).get(lord, {})
    house = pl.get("house", 0)
    theme = HOUSE_PAST.get(house, "life themes")
    sig = AD_YEAR_SIGNAL.get(lord, "A")
    maraka = {
        pc.get("longevity", {}).get("maraka_1", {}).get("lord"),
        pc.get("longevity", {}).get("maraka_2", {}).get("lord"),
    }
    if lord in maraka and lord in ("Moon", "Mars"):
        sig = "R"
    elif lord == "Venus" and house in (10, 11):
        sig = "G"
    elif lord == "Ketu":
        sig = "A"
    body = MD_PAST_BODY.get(lord, f"The {lord} sub-period sets the tone.")
    desc = f"{body.split('.')[0]} — routes through {house}th-house themes ({theme})."
    ad_note = f"{md_lord}–{lord} · {_ad_window(ad)}"
    return sig, desc, ad_note


def _build_year_themes(pc: dict) -> dict[int, tuple[str, str, str]]:
    today_yr = date.today().year
    out: dict[int, tuple[str, str, str]] = {}
    for yr in range(today_yr, today_yr + 7):
        mid = date(yr, 7, 1)
        md_lord, ad = _ad_at_date(pc, mid)
        if not ad:
            continue
        sig, desc, ad_note = _ad_year_theme(pc, md_lord, ad)
        out[yr] = (sig, desc, ad_note)
    return out


def _build_action_matrix(pc: dict) -> str:
    rows = ""
    ads = _future_ads(pc)[:4]
    if not ads:
        return "<p class='pred-body'>Action matrix requires a verified antardasha table.</p>"
    do_map = {
        "Venus": "Visible launches, negotiation, partnership dates, savings",
        "Ketu": "Rest, skill refresh, portfolio edits, short purposeful travel",
        "Mercury": "Contracts, certifications, document audits, clear communication",
        "Saturn": "Proof stacks, elder check-ins, structure, title conversations",
        "Jupiter": "Learning, mentorship, joint-resource clarity, gratitude practice",
        "Mars": "Strength training, competitive targets, disciplined exercise",
        "Moon": "Sleep rhythm, preventive checkups, household calm, hydration",
        "Sun": "Authority moves, expert positioning, moderate workload caps",
        "Rahu": "Network building with written terms, ambition with recovery days",
    }
    dont_map = {
        "Venus": "Unsigned handshakes, mystery equity, vanity projects that steal sleep",
        "Ketu": "Big irreversible exits, ego launches, speculative leverage",
        "Mercury": "Arguments under pressure, unsigned clauses, starting three threads at once",
        "Saturn": "Heroic overwork, shortcuts, promises without documentation",
        "Mars": "Elective surgery, high-risk bets, unchecked inflammation",
        "Moon": "All-nighters, ignored symptoms, emotional spending",
        "Sun": "Burnout visibility plays, unchecked pride, skipped medical baselines",
        "Rahu": "Verbal-only deals, body-sacrificing ambition, unverified travel",
    }
    success_map = {
        "Venus": "Income and recognition move together",
        "Ketu": "You feel mentally lighter without burning bridges",
        "Mercury": "Deliverables finish clean; contracts survive scrutiny",
        "Saturn": "Promotions feel boring-stable, not chaotic",
        "Jupiter": "Authority expands through earned proof, not hype",
        "Mars": "Energy channels into wins without collateral damage",
        "Moon": "Baseline health holds under rising duty",
        "Sun": "Visibility grows without heroic overwork",
        "Rahu": "Opportunity arrives with paperwork intact",
    }
    for ad in ads:
        lord = ad["ad_lord"]
        season = _ad_window(ad)
        rows += (
            f"<tr><td>{_e(season)}</td>"
            f"<td>{_e(do_map.get(lord, 'Steady effort aligned to chart emphasis'))}</td>"
            f"<td>{_e(dont_map.get(lord, 'Impulse moves without documentation'))}</td>"
            f"<td>{_e(success_map.get(lord, 'Progress feels deliberate, not chaotic'))}</td></tr>"
        )
    return f"""<table class="matrix">
  <tr><th>Season</th><th>Do more of</th><th>Do less of</th><th>Success signal</th></tr>
  {rows}
</table>"""


def _clean_prose(text: str, max_len: int = 260) -> str:
    t = html.unescape(re.sub(r"\s+", " ", (text or "").strip()))
    t = client_prose(t)
    t = re.sub(r"[,;]\s*$", ".", t)
    t = re.sub(r"\.\.+$", ".", t)
    if len(t) > max_len:
        cut = t[:max_len].rsplit(" ", 1)[0]
        cut = re.sub(r"[,;]\s*$", ".", cut)
        t = cut + ("." if not cut.endswith(".") else "")
    return t


def _personality_lane_bullets(extracted_path: str, client_name: str, dob: str, pc: dict) -> list[tuple[str, str]]:
    """Plain-English temperament lines from BNN + Bhardwaj book OCR (no semantic engine)."""
    bullets: list[tuple[str, str]] = []
    try:
        from bnn_chart import load_bnn_chart
        from bnn_chart_text import book_planet_sign

        ch, _bt = load_bnn_chart(extracted_path, client_name, dob, pc)
        moon = ch.planets.get("Moon", {})
        if moon.get("nakshatra"):
            nak = f"{moon['nakshatra']} Pada {moon.get('pada', '')}".strip()
            moon_txt = book_planet_sign(ch, "Moon")
            if moon_txt:
                bullets.append(("●", f"<strong>BNN — birth star {nak}.</strong> {_clean_prose(moon_txt)}"))
        ak = ch.atmakaraka()
        if ak and ak in ch.planets:
            ak_txt = book_planet_sign(ch, ak)
            if ak_txt:
                bullets.append(("✦", f"<strong>BNN — soul planet {ak}.</strong> {_clean_prose(ak_txt)}"))
        ll = ch.lord_of_house(1)
        if ll in ch.planets:
            ll_txt = book_planet_sign(ch, ll)
            if ll_txt:
                bullets.append(("→", f"<strong>BNN — chart ruler {ll}.</strong> {_clean_prose(ll_txt)}"))
    except Exception:
        pass

    try:
        from vedic_bhardwaj_report import BhardwajChart, _load_book

        chart = BhardwajChart(pc, _load_book())
        lagna_body = chart.book.get("lagna_signs", {}).get(chart.lagna, "")
        if lagna_body:
            bullets.append(("★", f"<strong>Bhardwaj — {chart.lagna} rising.</strong> {_clean_prose(lagna_body)}"))
        if chart.moon_sign and chart.moon_sign != chart.lagna:
            moon_body = chart.book.get("lagna_signs", {}).get(chart.moon_sign, "")
            if moon_body:
                bullets.append((
                    "◆",
                    f"<strong>Bhardwaj — emotional {chart.moon_sign} Moon.</strong> {_clean_prose(moon_body)}",
                ))
    except Exception:
        pass

    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for icon, line in bullets:
        key = re.sub(r"<[^>]+>", "", line).lower()[:80]
        if key in seen:
            continue
        seen.add(key)
        out.append((icon, line))
    return out[:4]


def _personality_pillar_text(
    pc: dict,
    by_dom: dict,
    extracted_path: str,
    client_name: str,
    dob: str,
) -> str:
    parts: list[str] = []
    cl = by_dom.get("personality")
    if cl and getattr(cl, "affirmation", None):
        parts.append(cl.affirmation)
    lagna = pc["meta"]["lagna_sign"]
    moon = pc.get("planets", {}).get("Moon", {}).get("sign", "")
    if not parts:
        parts.append(f"You present as quick and verbal with {lagna} rising and a precise {moon} emotional core.")
    for _icon, line in _personality_lane_bullets(extracted_path, client_name, dob, pc)[:3]:
        plain = _clean_prose(re.sub(r"<strong>[^<]+</strong>\s*", "", line), 220)
        if plain and plain.lower() not in " ".join(parts).lower():
            parts.append(plain)
    return " ".join(parts[:4])


def _build_nature_rows(pc: dict) -> str:
    """Warm, plain-English portrait — no house numbers, no planet jargon."""
    meta = pc["meta"]
    lagna = meta["lagna_sign"]
    pillar = pc.get("pillar", {})
    planets = pc.get("planets", {})
    ll_dig = pillar.get("lagna_lord_dignity", "neutral_sign")
    mars = planets.get("Mars", {})
    strong = ll_dig in ("exalted", "own_sign", "moolatrikona")

    rows: list[tuple[str, str]] = [
        ("★", f"At your core you carry the stamp of {lagna}. " + (
            "There's a real reserve of strength and staying power in you — when you commit to something "
            "with a bit of structure, you tend to outlast everyone else in the room."
            if strong else
            "Your wins are the earned kind — built on patience and proof rather than luck, which is "
            "precisely why they hold up over time."
        )),
        ("●", "You feel things more deeply than you let on. A calm home and a steady daily rhythm aren't "
              "luxuries for you — they're the fuel your focus runs on. When life at home wobbles, your "
              "concentration slips before anyone else even notices."),
        ("→", "Work is a big part of your story. You're built to think, refine, and put your name on things "
              "that hold up to scrutiny — and respect grows every time you leave behind a piece of work "
              "people can point to."),
        ("♠", "In love and in business, a little honesty early on saves you a lot of pain later. The bonds "
              "that test you are usually the ones where a shortcut got taken at the start — say the awkward "
              "thing sooner rather than later."),
    ]
    if mars.get("house") in (6, 10, 11):
        rows.append(("◆", "You've got a genuine competitive streak when it comes to earning and achieving. "
                          "Pointed at clear, measurable goals it pays off handsomely; let it leak into "
                          "arguments and it just wears you out."))
    rows.append(("✦", "Your quiet gift is recovery. After an overload — an illness, a stressful stretch, a "
                       "rough patch — you tend to bounce back faster than most people, as long as you rest "
                       "instead of pushing through in a panic."))
    nb = pillar.get("neecha_bhanga", {})
    if nb.get("neecha_bhanga_present"):
        rows.append(("✓", "Something in you that looks fragile on the surface is actually quietly protected. "
                          "Early struggles tend to turn into durable strength for you, not lasting setbacks."))
    elif nb.get("applicable") and not nb.get("neecha_bhanga_present"):
        rows.append(("!", "Some of your wins come the hard way — through steady, stacked-up proof rather than "
                          "lucky breaks. Frustrating at times, but it makes your success hard to take away."))
    elif ll_dig == "exalted":
        rows.append(("✓", "You've been handed an unusual reserve of stamina. Spend it through focus and "
                          "structure rather than scattered effort, and it will carry you a long way."))

    html_rows = ""
    for icon, line in rows[:7]:
        html_rows += f'<div class="nature-row"><div class="nature-icon">{icon}</div><div class="nature-text">{_e(line)}</div></div>\n'
    return html_rows


def _domain_headline(dom: str, cl: Cluster | None, pc: dict) -> str:
    if not cl or not cl.timing:
        return DOMAIN_HEADLINE.get(dom, DOMAIN_TITLE.get(dom, dom.title()))
    ad_lord = ""
    for ad in _future_ads(pc, include_current=True):
        if _ad_window(ad) in cl.timing or cl.timing in _ad_window(ad):
            ad_lord = ad["ad_lord"]
            break
    custom = {
        ("career", "Venus"): "Peak Professional Chapter Ahead",
        ("career", "Mercury"): "Contracts, Craft, and Career Delivery",
        ("career", "Ketu"): "Quiet Consolidation Before the Next Lift",
        ("finance", "Venus"): "Income and Savings Lift",
        ("marriage", "Venus"): "Partnership Warmth Returns",
        ("health", "Moon"): "Protect Your Baseline Now",
        ("health", "Mars"): "Channel Energy, Guard Vitality",
        ("travel", "Jupiter"): "Purposeful Travel Opens",
        ("travel", "Rahu"): "Foreign Links and Network Stretch",
    }
    return custom.get((dom, ad_lord), DOMAIN_HEADLINE.get(dom, DOMAIN_TITLE.get(dom, dom.title())))


def _build_challenge_boxes(pc: dict) -> str:
    health = _health_watch_windows(pc)
    peak = _peak_career_window(pc)
    boxes = ""
    if health:
        boxes += f"""
  <div class="challenge-box">
    <h3><span class="challenge-num">1</span> Look after your health early ({health[0]})</h3>
    <p>There's a stretch around this time when your body will simply ask for more care. The good news is you respond very well to <strong>acting early</strong> — so this is a nudge to book a check-up and tidy up your routine in advance, not something to fear.</p>
  </div>"""
    if peak:
        num = 2 if health else 1
        boxes += f"""
  <div class="challenge-box">
    <h3><span class="challenge-num">{num}</span> Don't burn out during your best window ({peak})</h3>
    <p>The same season that lifts your work can quietly eat your sleep if you say yes to everything. Protect a few rest days, put your wins and agreements in writing, and let this be the chapter people remember you for — without paying for it with your health.</p>
  </div>"""
    if not boxes:
        boxes = """
  <div class="challenge-box">
    <h3><span class="challenge-num">1</span> Steady beats sudden</h3>
    <p>Your life rewards a deliberate pace over big gambles. Time your bigger moves for when things feel settled rather than rushed, and keep a simple written record of what you agree to. Patience is genuinely your edge here.</p>
  </div>"""
    return boxes


def _timing_start_year(timing: str) -> int:
    m = re.search(r"(20\d{2})", timing or "")
    return int(m.group(1)) if m else 0


def _is_forward_timing(timing: str, min_year: int | None = None) -> bool:
    if not timing:
        return True
    yr = _timing_start_year(timing)
    if yr == 0:
        return True
    floor = min_year or date.today().year
    return yr >= floor


def _conf_badge(label: str) -> str:
    return {
        "VERY HIGH": "very-high", "HIGH": "high", "MODERATE": "moderate",
    }.get(label, "low")


def detect_focus_domain(question: str, engine: Optional["SemanticEngine"] = None) -> Optional[str]:
    """Map a client question to a life domain — keywords first, MiniLM fallback."""
    q = (question or "").strip()
    if not q:
        return None
    ql = q.lower()
    best_dom, best_hits = None, 0
    for dom, kws in QUESTION_KEYWORDS.items():
        hits = sum(1 for kw in kws if kw in ql)
        if hits > best_hits:
            best_hits, best_dom = hits, dom
    if best_dom and best_hits > 0:
        return best_dom
    try:
        from horary_precompute import detect_topic
        topic = detect_topic(q)
        mapped = HORARY_TOPIC_TO_DOMAIN.get(topic)
        if mapped:
            return mapped
    except Exception:
        pass
    if engine is not None:
        return engine.assign_domain(q)
    return None


def _conf_plain(n: int, label: str) -> str:
    if label == "VERY HIGH":
        return f"Very strong agreement — {n} independent methods"
    if label == "HIGH":
        return f"Strong agreement — {n} independent methods"
    if label == "MODERATE":
        return f"Solid pattern — {n} methods lean the same way"
    return f"Early signal — worth watching"


def _glob_lane(reports_dir: Path, pattern: str) -> Optional[Path]:
    hits = sorted(reports_dir.glob(pattern))
    return hits[-1] if hits else None


def _domain_from_section(title: str) -> str:
    for pat, dom in HTML_SECTION_DOMAIN:
        if pat.search(title):
            return dom
    return "unknown"


def _is_methodology_text(text: str) -> bool:
    return bool(METHODOLOGY_TEXT.search(text or ""))


def _normalize_signal(sig: Signal) -> Signal | None:
    """Drop methodology boilerplate; reroute education/personality fragments to the right domain."""
    if _is_methodology_text(sig.text):
        return None
    dom = sig.domain
    tl = sig.text.lower()
    if _is_misrouted_signal(sig, dom):
        return None
    if EDUCATION_TEXT.search(sig.text):
        dom = "children"
    elif dom == "travel" and re.search(r"personality and characteristics|dual nature|appearance:", tl):
        if not re.search(r"\b(travel|foreign|abroad|journey|pilgrim|relocation|visa|9th)\b", tl):
            dom = "personality"
    return Signal(sig.system, dom, sig.direction, sig.timing, client_prose(sig.text))


def _clean_signals(signals: list[Signal]) -> list[Signal]:
    out: list[Signal] = []
    for sig in signals:
        norm = _normalize_signal(sig)
        if norm:
            out.append(norm)
    return out


SECTION_CONF_DOMAIN: dict[str, str] = {
    "education": "children",
    "profession": "career",
    "wealth": "finance",
    "travel": "travel",
    "health": "health",
    "marriage": "marriage",
    "children": "children",
    "personality": "personality",
    "personality_table": "personality",
    "foundation": "personality",
    "dasha": "career",
    "antardasha": "children",
    "past_slice": "current",
    "karmic": "spiritual",
    "property": "property",
    "siblings": "children",
    "parents": "family",
}


def _map_lane_domain(domain: str, text: str) -> str:
    tl = (text or "").lower()
    if EDUCATION_TEXT.search(text or ""):
        return "children"
    if domain == "future":
        if re.search(r"\b(travel|foreign|abroad|relocation|visa)\b", tl):
            return "travel"
        if re.search(r"\b(spiritual|meditation|moksha|dharma|inner)\b", tl):
            return "spiritual"
        return "current"
    if domain == "family":
        return "children"
    if domain in DOMAINS:
        return domain
    return "personality"


def _conf_domain_from_claim(section_id: str, domain: str, text: str) -> str:
    sid = (section_id or "").lower()
    if sid in ("dasha", "antardasha"):
        return _map_lane_domain(domain, text)
    if sid in SECTION_CONF_DOMAIN:
        base = SECTION_CONF_DOMAIN[sid]
    else:
        base = domain
    return _map_lane_domain(base, text)


def _signals_from_lane_collectors(
    extracted_path: str,
    client_name: str,
    dob: str,
    pc: dict,
) -> tuple[list[Signal], set[str]]:
    """Structured predictions from live lane pipelines (BNN, KP, Mehta, etc.)."""
    out: list[Signal] = []
    systems: set[str] = set()
    try:
        claims, _meta = collect_all_lanes(extracted_path, client_name, dob, pc)
    except Exception:
        return out, systems
    seen: set[str] = set()
    for c in claims:
        if len(c.text.strip()) < 40:
            continue
        dom = _conf_domain_from_claim(c.section_id, c.domain, c.text)
        try:
            from bnn_book_data import clause_ok_for_domain
            if c.lane == "BNN" and not clause_ok_for_domain(c.text, dom):
                continue
        except ImportError:
            pass
        key = (c.lane, dom, c.text[:100].lower())
        if key in seen:
            continue
        seen.add(key)
        systems.add(c.lane)
        out.append(Signal(
            c.lane,
            dom,
            c.direction,
            c.timing,
            c.text.strip()[:600],
        ))
    return out, systems


def _html_pred_blocks(raw: str) -> list[tuple[str, str]]:
    """Return (section_title, prediction_text) from lane HTML structure."""
    blocks: list[tuple[str, str]] = []
    parts = re.split(r"(<h[12][^>]*>.*?</h[12]>|<h3[^>]*>.*?</h3>)", raw, flags=re.S | re.I)
    section = ""
    for part in parts:
        if re.match(r"<h[123]", part, re.I):
            section = _strip_html(part).strip()
            continue
        for m in re.finditer(
            r'<(?:p|div)[^>]*class="[^"]*(?:pred|verdict-line|callout-future|callout-green|callout-amber)[^"]*"[^>]*>(.*?)</(?:p|div)>',
            part,
            flags=re.S | re.I,
        ):
            txt = _strip_html(m.group(1)).strip()
            if len(txt) >= 50:
                blocks.append((section, txt))
    return blocks


def _extract_html_signals(
    reports_dir: Path,
    slug: str,
    *,
    skip_systems: set[str] | None = None,
    max_per_lane: int = 5,
) -> list[Signal]:
    """Pull prediction sentences from lane HTML (fallback when collectors miss a lane)."""
    out: list[Signal] = []
    seen: set[str] = set()
    skip_systems = skip_systems or set()
    kw_positive = re.compile(r"\b(peak|strong|favour|auspicious|growth|promotion|harmony|gains?|excellent|protective|good sign)\b", re.I)
    kw_caution = re.compile(r"\b(watch|caution|risk|maraka|fatigue|delay|stress|debilitat|weak|challeng|needs attention)\b", re.I)

    for system, pat in LANE_FILES.items():
        if system in skip_systems:
            continue
        path = _glob_lane(reports_dir, pat.format(slug=slug))
        if not path:
            continue
        raw = path.read_text(encoding="utf-8", errors="ignore")
        added = 0

        for section, chunk in _html_pred_blocks(raw):
            if added >= max_per_lane:
                break
            if re.search(r"methodology|core rules|book-backed", section, re.I):
                continue
            chunk = re.sub(r"\s+", " ", chunk).strip()
            chunk = client_prose(chunk)
            if len(chunk) < 50 or len(chunk) > 420 or HTML_SKIP.search(chunk) or _is_methodology_text(chunk):
                continue
            key = chunk[:90].lower()
            if key in seen:
                continue
            seen.add(key)
            dom = _domain_from_section(section)
            direction = "caution" if kw_caution.search(chunk) else ("positive" if kw_positive.search(chunk) else "neutral")
            timing = ""
            m = re.search(r"(20\d{2}(?:\s*[–-]\s*20\d{2})?|[A-Z][a-z]{2}\s+20\d{2})", chunk)
            if m:
                timing = m.group(1)
            out.append(Signal(system, dom, direction, timing, chunk))
            added += 1

        if added >= max_per_lane:
            continue

        text = _strip_html(raw)
        for chunk in re.split(r"(?<=[.!?])\s+", text):
            if added >= max_per_lane:
                break
            chunk = chunk.strip()
            chunk = client_prose(chunk)
            if len(chunk) < 70 or len(chunk) > 320 or HTML_SKIP.search(chunk):
                continue
            if not re.search(r"\b(career|health|wealth|marriage|child|travel|foreign|spiritual|partner|income|period|window|peak|promotion|risk|property|profession)\b", chunk, re.I):
                continue
            key = chunk[:80].lower()
            if key in seen:
                continue
            seen.add(key)
            direction = "caution" if kw_caution.search(chunk) else ("positive" if kw_positive.search(chunk) else "neutral")
            timing = ""
            m = re.search(r"(20\d{2}(?:\s*[–-]\s*20\d{2})?|[A-Z][a-z]{2}\s+20\d{2})", chunk)
            if m:
                timing = m.group(1)
            out.append(Signal(system, "unknown", direction, timing, chunk))
            added += 1
    return out


def _signals_from_precompute(pc: dict) -> list[Signal]:
    """Deterministic high-confidence signals with exact dates from this chart only."""
    s: list[Signal] = []
    meta = pc["meta"]
    ll = meta["lagna_lord"]
    lagna = meta["lagna_sign"]
    vim = pc.get("vimshottari", {})
    md = vim.get("current_md", {}).get("md_lord", "")
    ad = next((a for a in vim.get("current_md_antardashas", []) if a.get("status") == "current"), {})
    ad_lord = ad.get("ad_lord", "")
    ad_rng = _ad_window(ad) if ad else ""

    if md and ad_lord:
        s.append(Signal("Vimshottari", "current", "neutral", ad_rng,
                        f"Currently in {md} mahadasha with {ad_lord} antardasha ({ad_rng}) — themes follow this chart's verified sub-period table."))

    house_dom = {5: "children", 7: "marriage", 10: "career", 11: "finance", 6: "health", 9: "travel", 4: "property"}
    for a in vim.get("current_md_antardashas", []):
        if a.get("status") not in ("current", "future"):
            continue
        lord = a["ad_lord"]
        rng = _ad_window(a)
        pl = pc.get("planets", {}).get(lord, {})
        house = pl.get("house", 0)
        dig = pl.get("dignity", "")
        theme = HOUSE_PAST.get(house, "life experience")
        txt = f"{md}–{lord} antardasha ({rng}): themes route through the {house}th-house life area ({theme})."
        direction = "positive" if dig in ("exalted", "own_sign", "moolatrikona") or house in (5, 9, 10, 11) else "neutral"
        if lord in ("Saturn", "Rahu", "Ketu") and house in (6, 8, 12):
            direction = "caution"
        domain = house_dom.get(house, "career")
        if lord == "Venus" and house in (10, 11):
            direction = "positive"
            txt = (f"{md}–Venus antardasha ({rng}) activates Venus in the {house}th house — "
                   f"a strong window for recognition and income lift in this map.")
            s.append(Signal("Vimshottari", "finance", "positive", rng,
                            f"Income and savings capacity improve as Venus runs ({rng})."))
            if house != 11:
                s.append(Signal("Vimshottari", "marriage", "positive", rng,
                                f"Partnership warmth can improve as Venus runs ({rng})."))
        s.append(Signal("Vimshottari", domain, direction, rng, txt))

    lg_ctx = build_longevity_context(pc)
    maraka_lords = {lg_ctx.maraka_1, lg_ctx.maraka_2}
    crit_mb = set(lg_ctx.critical_mb)
    for a in vim.get("current_md_antardashas", []):
        if a.get("status") not in ("current", "future"):
            continue
        lord = a["ad_lord"]
        if lord not in maraka_lords:
            continue
        _cls, _mb, risk, theme = classify_ad_risk(pc, lord)
        if risk not in ("Moderate", "High", "Highest"):
            continue
        crit = lord in crit_mb
        rng = _ad_window(a)
        note = " with sensitive-degree (book MB) activation - build habits before this window." if crit else " - elevated health awareness advised."
        s.append(Signal("Longevity", "health", "caution" if risk in ("High", "Highest") else "neutral", rng,
                        f"Primary maraka sub-chapter ({rng}): {theme}{note} Educational only."))

    for sig in longevity_signals(pc):
        s.append(Signal(sig["system"], sig["domain"], sig["direction"], sig["timing"], sig["text"]))

    cy = pc.get("rtvd", {}).get("current_year", {})
    if cy:
        h = cy.get("house_active", 0)
        dom = house_dom.get(h, "career")
        yl = cy.get("year_lord", "?")
        ysig = cy.get("year_lord_sign", "?")
        yh = cy.get("year_lord_house", "?")
        dig = cy.get("year_lord_dignity", "neutral")
        yr = cy.get("calendar_year", "")
        direction = "positive" if dig in ("exalted", "own_sign", "moolatrikona") else "neutral"
        if h in (6, 8, 12) and dig not in ("exalted", "own_sign", "moolatrikona"):
            direction = "caution"
        s.append(Signal(
            "RTVD", dom, direction, str(yr),
            f"RTVD age {cy.get('age')} ({yr}): {h}th-house year led by {yl} in {ysig} (house {yh}, {dig.replace('_', ' ')}).",
        ))

    yg = pc.get("yogini", {}).get("current_yogini", {})
    if yg:
        yrng = f"{_parse_date_short(yg.get('start', ''))} – {_parse_date_short(yg.get('end', ''))}"
        s.append(Signal("Yogini", "current", "caution" if yg.get("tone") == "inauspicious" else "positive",
                        yrng,
                        f"Yogini {yg.get('yogini')} ({yg.get('lord')}) mahadasa ({yrng}) — tone is {yg.get('tone', 'mixed')} in this chart."))

    nxt = pc.get("yogini", {}).get("next_yogini", {})
    if nxt:
        nrng = f"{_parse_date_short(nxt.get('start', ''))} – {_parse_date_short(nxt.get('end', ''))}"
        s.append(Signal("Yogini", "career", "positive" if nxt.get("tone") != "inauspicious" else "neutral",
                        nrng,
                        f"Next Yogini {nxt.get('yogini')} ({nxt.get('lord')}) opens from {nrng}."))

    num = pc.get("numerology", {})
    lp = num.get("life_path", "")
    if lp:
        s.append(Signal("Numerology", "personality", "neutral", "birth chart",
                        f"Life path {lp} and expression {num.get('expression', '?')} colour how initiative and introspection blend in this name map."))
        yr = date.today().year
        for block in num.get("maha_dasha", []):
            if block.get("start_year", 0) <= yr < block.get("end_year", 0):
                s.append(Signal("Numerology", "career", "positive", f"{block['start_year']} – {block['end_year']}",
                                f"Numerology maha dasha of {block['lord']} runs through age band {block['start_year']}–{block['end_year']} for this chart."))
                break

    pillar = pc.get("pillar", {})
    ll_h = pillar.get("lagna_lord_house", 1)
    ll_dig = pillar.get("lagna_lord_dignity", "neutral")
    nb = pillar.get("neecha_bhanga", {})
    nb_txt = ""
    if nb.get("neecha_bhanga_present"):
        cancel = nb.get("cancelling_planet", "a supporting planet")
        nb_txt = f" Neecha Bhanga via {cancel} converts friction into earned strength."
    elif nb.get("applicable"):
        nb_txt = f" {ll} debility in {pillar.get('lagna_lord_sign', '?')} adds friction — wins demand proof stacks."
    s.append(Signal("Pillar", "personality", "positive" if ll_dig in ("exalted", "own_sign", "moolatrikona") or nb.get("neecha_bhanga_present") else "neutral",
                    "life chart",
                    f"Lagna lord {ll} in the {ll_h}th house ({ll_dig}) anchors identity in {HOUSE_PAST.get(ll_h, 'this life area')}.{nb_txt}"))

    return s


class SemanticEngine:
    def __init__(self):
        from local_models import load_sentence_transformer

        self.model = load_sentence_transformer()
        self._anchor_emb: dict[str, np.ndarray] = {}
        self._book_emb: dict[tuple[str, str, int], np.ndarray] = {}
        for dom, anchors in THEME_ANCHORS.items():
            self._anchor_emb[dom] = self.model.encode(anchors, normalize_embeddings=True)
        for dom, dirs in BOOK_LINES.items():
            for direction, lines in dirs.items():
                for i, line in enumerate(lines):
                    self._book_emb[(dom, direction, i)] = self.model.encode([line], normalize_embeddings=True)[0]

    def assign_domain(self, text: str) -> str:
        emb = self.model.encode([text], normalize_embeddings=True)[0]
        best_dom, best_sc = "career", -1.0
        for dom, amat in self._anchor_emb.items():
            sc = float(np.max(amat @ emb))
            if sc > best_sc:
                best_sc, best_dom = sc, dom
        return best_dom

    def _best_snippet(self, texts: list[str], direction: str) -> str:
        if not texts:
            return ""
        uniq = list(dict.fromkeys(t.strip() for t in texts if t.strip()))[:8]
        if len(uniq) == 1:
            return _snippet(uniq[0], 300)
        anchors = {
            "positive": "growth success improvement favourable strong good peak harmony gains protective clear low risk",
            "caution": "delay risk watch caution stress illness obstacle debt friction maraka challenging",
            "neutral": "life themes pattern rhythm steady mixed balance maintenance",
        }
        anchor = self.model.encode([anchors.get(direction, anchors["neutral"])], normalize_embeddings=True)[0]
        embs = self.model.encode(uniq, normalize_embeddings=True)
        best_i = int(np.argmax(embs @ anchor))
        return _snippet(uniq[best_i], 300)

    def _synthesize_affirmation(
        self,
        members: list[Signal],
        direction: str,
        domain: str,
        timing: str,
    ) -> str:
        """Build verdict prose from actual lane/precompute sentences — not generic templates."""
        texts = [m.text for m in members if m.text.strip()]
        # Prefer lane-sourced lines over dasha-house routing boilerplate.
        lane_texts = [m.text for m in members if m.system not in ("Vimshottari", "RTVD", "Numerology", "Pillar")]
        if lane_texts:
            texts = lane_texts
        if texts:
            synth = self._best_snippet(texts, direction)
            if synth:
                return client_prose(synth)
        return self._pick_line_fallback(domain, direction)

    def _pick_line_fallback(self, domain: str, direction: str) -> str:
        title = DOMAIN_TITLE.get(domain, domain.replace("_", " ").title())
        return (
            f"[SPECULATIVE — incomplete lane data for {title}] "
            "Run the full report pipeline or supply dated life events before relying on this area. "
            "No generic prediction is substituted for missing book-backed lane output."
        )

    def cluster_signals(self, signals: list[Signal], threshold: float = 0.52) -> list[Cluster]:
        for sig in signals:
            if sig.domain == "unknown":
                sig.domain = self.assign_domain(sig.text)

        # Domain-level summary clusters (main verdicts) + fine clusters for dashboard
        embs = self.model.encode([x.text for x in signals], normalize_embeddings=True)
        domain_clusters: list[Cluster] = []

        for dom in DOMAINS:
            idxs = [i for i, s in enumerate(signals) if s.domain == dom]
            if not idxs:
                continue
            members = [signals[i] for i in idxs if not _is_misrouted_signal(signals[i], dom)]
            if not members:
                continue
            systems = sorted({m.system for m in members})
            pos = sum(1 for m in members if m.direction == "positive")
            cau = sum(1 for m in members if m.direction == "caution")
            neu = sum(1 for m in members if m.direction == "neutral")
            # Weight lane systems over generic dasha routing for direction vote.
            lane_pos = sum(1 for m in members if m.direction == "positive" and m.system not in ("Vimshottari",))
            lane_cau = sum(1 for m in members if m.direction == "caution" and m.system not in ("Vimshottari",))
            if lane_pos or lane_cau:
                direction = "positive" if lane_pos >= lane_cau else ("caution" if lane_cau > lane_pos else "neutral")
            else:
                direction = "positive" if pos >= cau else ("caution" if cau > pos else "neutral")
            if dom == "health":
                lg = [m for m in members if m.system == "Longevity"]
                if lg and any("low risk" in m.text.lower() or "no strict" in m.text.lower() for m in lg):
                    hard_cau = sum(
                        1 for m in members
                        if m.direction == "caution" and m.system not in ("Vimshottari", "RTVD")
                    )
                    if hard_cau < 2:
                        direction = "positive"
            timings = [m.timing for m in members if m.timing]
            timing = max(timings, key=len) if timings else ""
            affirmation = self._synthesize_affirmation(members, direction, dom, timing)
            domain_clusters.append(Cluster(dom, direction, timing, systems, [m.text for m in members[:6]],
                                             affirmation, _conf_label(len(systems)), float(len(systems))))

        # Sub-clusters for semantic dashboard (optional detail)
        fine: list[Cluster] = []
        used = [False] * len(signals)
        for i, sig in enumerate(signals):
            if used[i]:
                continue
            idxs = [i]
            used[i] = True
            for j in range(i + 1, len(signals)):
                if used[j] or signals[j].domain != sig.domain:
                    continue
                if float(embs[i] @ embs[j]) >= threshold:
                    idxs.append(j)
                    used[j] = True
            if len(idxs) < 2:
                continue
            members = [signals[k] for k in idxs]
            systems = sorted({m.system for m in members})
            directions = [m.direction for m in members]
            direction = max(set(directions), key=directions.count)
            timings = [m.timing for m in members if m.timing]
            timing = timings[0] if timings else ""
            centroid = np.mean(embs[idxs], axis=0)
            centroid = centroid / (np.linalg.norm(centroid) + 1e-9)
            fine.append(Cluster(sig.domain, direction, timing, systems,
                                [m.text for m in members],
                                self._synthesize_affirmation(members, direction, sig.domain, timing),
                                _conf_label(len(systems)), float(len(systems))))

        out = domain_clusters + fine
        out.sort(key=lambda c: (-c.score, c.domain))
        return out

    def _pick_line(self, domain: str, direction: str, centroid: np.ndarray, timing: str = "") -> str:
        return self._pick_line_fallback(domain, direction)


def _signals_from_palm(palm_analysis: Optional[dict]) -> list[Signal]:
    if not palm_analysis:
        return []
    try:
        from palm_api.pipeline import signals_for_confluence
        raw = signals_for_confluence(palm_analysis)
    except Exception:
        return []
    out: list[Signal] = []
    for r in raw:
        out.append(Signal(
            r.get("system", "Palmistry"),
            r.get("domain", "unknown"),
            r.get("direction", "neutral"),
            r.get("timing", ""),
            r.get("text", ""),
        ))
    return out


def _domain_signal_rows(signals: list[Signal], domain: str) -> str:
    rows = ""
    sys_map = _signals_by_system(signals, domain)
    for sys, sig in sorted(sys_map.items()):
        badge = {"positive": "hi", "caution": "lo", "neutral": "mod"}[sig.direction]
        rows += (f"<tr><td>{sys}</td><td><span class='badge {badge}'>✓</span></td>"
                 f"<td>{_e(_snippet(sig.text, 200))}</td><td>{_e(sig.timing)}</td></tr>")
    return rows


def _is_misrouted_signal(sig: Signal, domain: str) -> bool:
    if _is_methodology_text(sig.text):
        return True
    tl = sig.text.lower()
    try:
        from bnn_book_data import clause_ok_for_domain
        if sig.system == "BNN" and not clause_ok_for_domain(sig.text, domain):
            return True
    except ImportError:
        pass
    if domain in ("children", "speech", "health", "career", "finance", "travel", "education", "current"):
        if FAMILY_BLEED.search(sig.text):
            return True
    if domain == "health" and EDUCATION_TEXT.search(sig.text):
        return True
    if domain == "career" and EDUCATION_TEXT.search(sig.text):
        return True
    if domain == "travel" and re.search(r"personality and characteristics|dual nature|appearance:", tl):
        if not re.search(r"\b(travel|foreign|abroad|journey|pilgrim|relocation|visa)\b", tl):
            return True
    if domain == "property" and re.search(r"health & safety.*land.*bank|atm|medical shop", tl):
        return True
    return False


def _signals_by_system(signals: list[Signal], domain: str) -> dict[str, Signal]:
    out: dict[str, Signal] = {}
    for sig in signals:
        if sig.domain != domain or _is_misrouted_signal(sig, domain):
            continue
        if sig.system not in out or len(sig.text) > len(out[sig.system].text):
            out[sig.system] = sig
    return out


def _snippet(text: str, n: int = 140) -> str:
    t = html.unescape(re.sub(r"\s+", " ", text).strip())
    return t if len(t) <= n else t[: n - 1].rsplit(" ", 1)[0] + "…"


def _nature_html(
    engine: SemanticEngine,
    signals: list[Signal],
    pc: dict,
    *,
    extracted_path: str = "",
    client_name: str = "",
    dob: str = "",
) -> str:
    body = _build_nature_rows(pc)
    if extracted_path and client_name and dob:
        for icon, line in _personality_lane_bullets(extracted_path, client_name, dob, pc):
            # Strip method labels (e.g. "BNN — birth star …") and any markup so the
            # reader hears the trait, not the technique behind it.
            plain = re.sub(r"^\s*<strong>[^<]*</strong>\s*", "", line)
            plain = re.sub(r"<[^>]+>", "", plain).strip()
            if not plain or _JARGON_RX.search(plain) or _ALARM_RX.search(plain):
                continue
            body += f'<div class="nature-row"><div class="nature-icon">{icon}</div><div class="nature-text">{_e(plain)}</div></div>\n'
    return body


def _past_html(pc: dict) -> str:
    chapters = _build_past_chapters(pc)
    if not chapters:
        chapters = [(
            "Life chapters",
            "Past reconstruction requires a verified dasha table — rerun after extract precompute completes.",
        )]
    return "".join(
        f'<div class="past-card"><div class="past-label">{_e(lbl)}</div><div class="pred-body">{_e(body)}</div></div>'
        for lbl, body in chapters
    )


def _roadmap_rows(pc: dict, by_dom: dict[str, Cluster]) -> str:
    """Year-by-year traffic lights from this chart's antardashas + domain votes."""
    year_themes = _build_year_themes(pc)
    rows = ""
    for yr in sorted(year_themes):
        sig, theme, ad_note = year_themes[yr]
        tg_cls = {"G": "tg-g", "A": "tg-a", "R": "tg-r"}[sig]
        dot = {"G": "🟢", "A": "🟡", "R": "🔴"}[sig]
        _, ad = _ad_at_date(pc, date(yr, 7, 1))
        ad_lord = ad["ad_lord"] if ad else ""
        car = by_dom.get("career")
        car_dot = "🟢" if car and car.direction == "positive" and sig == "G" else dot
        if ad:
            _cls, _mb, risk, _theme = classify_ad_risk(pc, ad_lord)
            health_dot = health_light_for_risk(risk)
        else:
            health_dot = dot
        family_dot = "🟢" if ad_lord == "Venus" else dot
        travel_dot = "🟢" if ad_lord in ("Jupiter", "Rahu") or (ad and pc.get("planets", {}).get(ad_lord, {}).get("house") in (9, 12)) else dot
        rows += f"""<tr>
  <td><strong>{yr}</strong></td><td>{_e(ad_note)}</td>
  <td class="tg {tg_cls}">{car_dot}</td>
  <td class="tg {tg_cls}">{dot}</td>
  <td class="tg {tg_cls}">{health_dot}</td>
  <td class="tg {tg_cls}">{family_dot}</td>
  <td class="tg {tg_cls}">{travel_dot}</td>
  <td>{_e(theme)}</td></tr>"""
    return rows


def _roadmap_detail_rows(pc: dict) -> str:
    md_lord = pc.get("vimshottari", {}).get("current_md", {}).get("md_lord", "")
    rows = ""
    for a in _future_ads(pc):
        rng = _ad_window(a)
        theme, lights = _ad_lights(pc, a)
        rows += f"""<tr>
  <td><strong>{_e(rng)}</strong></td><td>{md_lord}–{a['ad_lord']}</td>
  {''.join(f'<td class="tg">{d}</td>' for d in lights)}
  <td>{_e(theme)}</td></tr>"""
    return rows


def _css_confluence() -> str:
    return confluence_css()


def _css_user() -> str:
    return client_css()


# ─────────────────────────────────────────────────────────────────────
#  Human, daily-life presentation layer
#  All charts / dasha / longevity maths run upstream. Nothing below
#  exposes house numbers, planet jargon, "maraka", method names or vote
#  counts. The reader just hears about their own life, in plain words.
# ─────────────────────────────────────────────────────────────────────

LIFE_AREA_TITLE = {
    "career": "Career & Work",
    "finance": "Money & Wealth",
    "marriage": "Love, Marriage & Your Partner",
    "children": "Children & Parenting",
    "parents": "Parents & The Elders You Care For",
    "property": "Home, Land & Property",
    "health": "Health, Energy & Recovery",
    "legal": "Legal Matters & Disputes",
    "travel": "Travel & New Horizons",
    "spiritual": "Inner Peace & Meaning",
}

LIFE_AREA_LEAD = {
    "career": "Your work, ambition and the name you build for yourself.",
    "finance": "Money coming in, what you keep, and peace of mind about it.",
    "marriage": "Your partner, closeness, and the health of your love life.",
    "children": "Children, raising them, and the things you create with love.",
    "parents": "Your mother, father, and the elders who lean on you.",
    "property": "A settled base — home, land, a vehicle, a place that's yours.",
    "health": "Your body, your energy, and bouncing back when illness strikes.",
    "legal": "Agreements, paperwork, disputes and official matters.",
    "travel": "Journeys, moving cities or countries, and chances far from home.",
    "spiritual": "Quiet, meaning, and the part of life that isn't about doing.",
}


def _long_date(dt) -> str:
    """Cross-platform 'D Month YYYY' (the %-d directive is Linux-only and crashes on Windows)."""
    return f"{dt.day} {dt.strftime('%B %Y')}"


def _conf_feel(label: str) -> tuple[str, str]:
    """Turn an internal confidence label into a warm phrase + pill colour."""
    l = (label or "").upper()
    if l == "VERY HIGH":
        return ("Very clear — many threads point the same way", "hi")
    if l == "HIGH":
        return ("A strong, steady signal", "hi")
    if l == "MODERATE":
        return ("Likely — worth planning around", "mid")
    if l == "LOW":
        return ("An early hint, not a promise", "lo")
    return ("A gentle possibility to keep in mind", "lo")


def _friendly_timing(t: str) -> str:
    t = (t or "").strip()
    if not t:
        return "An ongoing thread in your life"
    return t


def _area_tone(dom: str, cl: Optional["Cluster"]) -> str:
    if dom in ("health", "legal") and (not cl or cl.direction != "positive"):
        return "blue"
    if cl and cl.direction == "caution":
        return "amber"
    if cl and cl.direction == "positive":
        return "green"
    return "blue"


def _fallback_area_line(dom: str) -> str:
    lines = BOOK_LINES.get(dom, {})
    for key in ("neutral", "positive", "caution"):
        if lines.get(key):
            return lines[key][0]
    return "This part of life moves quietly for now — steady habits matter more than big moves."


# ── Chart-specific, honest insight engine ─────────────────────────────
#  Specificity comes from THIS chart's house-lord placement, strength,
#  agree/caution direction and real timing windows — different for every
#  person. The truth (including weak spots) is named plainly and paired
#  with a concrete remedy, in everyday words.
_DUSTHANA = {6, 8, 12}
_KENDRA = {1, 4, 7, 10}
_TRIKONA = {5, 9}

DOMAIN_HOUSE = {
    "career": 10, "finance": 2, "marriage": 7, "children": 5,
    "property": 4, "travel": 9, "spiritual": 12,
}
DOMAIN_SUBJECT = {
    "career": "Your standing at work",
    "finance": "Your money",
    "marriage": "Your marriage",
    "children": "Your family life",
    "property": "A settled home of your own",
    "travel": "Your life away from home",
    "spiritual": "Your inner life",
}
REMEDY_ACTION = {
    "Sun": "lead with quiet, honest effort instead of ego, and keep your father and elders close",
    "Moon": "protect your sleep and peace of mind, and keep home life calm",
    "Mars": "burn off the heat through exercise and clear goals rather than conflict",
    "Mercury": "slow down, read the details, and actually finish what you start",
    "Jupiter": "act with integrity, take good advice, and keep learning",
    "Venus": "put real time into your relationships and avoid shortcuts in love and money",
    "Saturn": "be patient and consistent — show up every single day and let time work for you",
    "Rahu": "get every promise in writing and stay away from get-rich-quick temptations",
    "Ketu": "let go of what is already finished and make a little room for stillness",
}
CUR_SEASON = {
    "Ketu": "This is a winding-down, clearing-out season — quieter on the surface while a lot settles underneath.",
    "Venus": "This is one of life's warmer, more comfortable seasons — relationships, ease and small pleasures come more naturally.",
    "Mercury": "This is a busy, communicative season — deals, learning and organising things are where your energy flows best.",
    "Saturn": "This is a serious, build-the-foundations season — slower and heavier, but the work you do now genuinely lasts.",
    "Mars": "This is a high-energy, push-forward season — plenty of drive, with a real need to guard your temper and your rest.",
    "Jupiter": "This is an expansive, growth-minded season — good for learning, guidance and widening your horizons.",
    "Sun": "This is a step-into-the-light season — more visibility and responsibility, and a pull to stand on your own authority.",
    "Moon": "This is an emotionally tuned season — home, family and your inner weather matter more than usual.",
    "Rahu": "This is an ambitious, reaching season — new circles and big wants, best handled with your feet on the ground.",
}


def _current_season_text(pc: dict) -> str:
    return CUR_SEASON.get(_current_ad_lord(pc),
                          "You're in a clearly defined chapter of life right now — a real season with its own flavour, not a vague mood.")


def _strength_sentence(subject: str, lh, dig: str) -> str:
    if isinstance(lh, int) and lh in _DUSTHANA:
        place = ("is hard-won ground for you — it carries real friction and tends to open up only when you "
                 "face it directly, with patience")
    elif isinstance(lh, int) and lh in _KENDRA:
        place = "stands on solid foundations and shows up strongly through your life"
    elif isinstance(lh, int) and lh in _TRIKONA:
        place = "carries a genuine thread of good fortune"
    elif lh == 11:
        place = "builds up steadily through persistence and the right people around you"
    elif lh == 2:
        place = "is tied closely to your security and to what you manage to keep"
    elif lh == 3:
        place = "rewards your own initiative far more than waiting on luck"
    else:
        place = "moves in a steady, ordinary rhythm"
    if dig == "exalted":
        strg = " The force behind it is genuinely powerful — a real strength you can build on."
    elif dig in ("own_sign", "moolatrikona"):
        strg = " It's well-supported and dependable."
    elif dig == "debilitated":
        strg = (" It starts on the back foot, so what you gain here is earned through effort and the right "
                "course-correction — not handed to you.")
    else:
        strg = " It's neither especially blessed nor cursed; your consistency is what tips it your way."
    return f"{subject} {place}.{strg}"


def _domain_insight(dom: str, pc: dict, cl: Optional["Cluster"]) -> str:
    """One honest, chart-specific paragraph for a life area — truth first, remedy if weak."""
    h = DOMAIN_HOUSE.get(dom)
    rec = get_house_lord(pc, h) if h else {}
    lord = rec.get("lord", "")
    lh = rec.get("lord_house")
    dig = rec.get("lord_dignity", "")
    subject = DOMAIN_SUBJECT.get(dom, "This part of your life")
    direction = cl.direction if cl else "neutral"
    timing = cl.timing if cl and getattr(cl, "timing", "") else ""
    out = _strength_sentence(subject, lh, dig)
    weak = (dig == "debilitated") or (isinstance(lh, int) and lh in _DUSTHANA)
    if direction == "caution" or weak:
        action = REMEDY_ACTION.get(lord, "tackle small problems early, before they grow")
        out += (" Be honest with yourself here rather than just hopeful — if something feels off in this area, "
                f"treat it as real and deal with it early. What genuinely helps: {action}.")
    elif direction == "positive":
        out += " This is one of your brighter areas right now — put steady effort behind it and it pays you back well."
    else:
        out += " No alarms here — keep your habits steady and it stays on your side."
    if timing:
        out += f" The stretch that matters most: {timing}."
    return out


def _health_insight(pc: dict, cl: Optional["Cluster"], lctx) -> str:
    rec = get_house_lord(pc, 6)
    dig = rec.get("lord_dignity", "")
    parts: list[str] = []
    if dig in ("exalted", "own_sign", "moolatrikona"):
        parts.append("Your basic constitution is sturdy — you're built to recover well, provided you actually let yourself rest.")
    elif dig == "debilitated":
        parts.append("Your constitution isn't bulletproof, so it genuinely pays to stay ahead of your health rather than assume you'll always bounce back.")
    else:
        parts.append("Your health is fundamentally workable — it holds up on routine and slips mainly when you run yourself down for too long.")
    watch = getattr(lctx, "health_watch_windows", []) if lctx else []
    maxr = getattr(lctx, "max_future_risk", "") if lctx else ""
    if watch:
        parts.append(f"There's a more sensitive stretch around {watch[0]} — nothing to be frightened of, but a clear signal to get a full check-up, sleep properly and ease your workload before it arrives.")
    elif maxr in ("High", "Highest"):
        parts.append("A couple of seasons ahead will ask for more rest and a proper check-up — book them in like service appointments, in advance.")
    else:
        parts.append("The years just ahead look steady on the health front; your usual good habits and a yearly check-up are plenty.")
    parts.append("And your real edge is recovery: when you give yourself permission to rest fully, you heal faster than most people do.")
    return " ".join(parts)


_JARGON_RX = re.compile(
    r"(\b\d+\s*(st|nd|rd|th)\s*(house|lord)\b|\bhouse\s+lord\b|\bmahadasha\b|\bantardasha\b|"
    r"\bdasha\b|\bdusthana\b|\bsav\b|\bbav\b|\bkaraka\b|debilitat\w*|exalt\w*|\blagna\b|"
    r"\bnakshatra\b|\bmaraka\b|\bmrityu\w*|\btrikona\b|\bkendra\b|ashtakavarga|\bbindus?\b|"
    r"\bcusp\b|sub-?lord|\bnavamsa\b|\bd9\b|\bd10\b|\bgraha\b|conjunct\w*|\bretrograde\b|"
    r"\bSAV\s*\d+|\bdeg\b|chapter ruler sits)",
    re.I,
)
_ALARM_RX = re.compile(
    r"\b(death|dies?|dying|attaining death|filthy|humiliat\w*|\bservant\b|\bwidow\w*|"
    r"poverty|destruction|cursed|sinful|immoral|leprosy|imprison\w*|"
    r"loss of (wife|husband|son|wealth|spouse)|will be sick|absurd|lazy)\b",
    re.I,
)


def _humanize_affirmation(text: str, domain: str, direction: str) -> str:
    """Keep clean, human affirmations; quietly swap jargon/alarming book text for a warm line."""
    t = client_prose((text or "").strip())
    if not t or len(t) < 25 or _JARGON_RX.search(t) or _ALARM_RX.search(t):
        lines = BOOK_LINES.get(domain, {})
        for key in (direction, "neutral", "positive", "caution"):
            if lines.get(key):
                return lines[key][0]
        return _fallback_area_line(domain)
    return t


def _current_ad_lord(pc: dict) -> str:
    vim = pc.get("vimshottari", {})
    ad = next((a for a in vim.get("current_md_antardashas", []) if a.get("status") == "current"), {})
    return ad.get("ad_lord", "")


def _parents_body(pc: dict) -> str:
    """Warm, plain-English reading of bonds with mother, father and elders."""
    planets = pc.get("planets", {})
    sun = planets.get("Sun", {})
    moon = planets.get("Moon", {})

    def warmth(dig: str) -> str:
        if dig in ("exalted", "own_sign", "moolatrikona"):
            return "a supportive, steadying"
        if dig == "debilitated":
            return "a loving but sometimes testing"
        return "a generally warm, workable"

    fb = warmth(sun.get("dignity", ""))
    mb = warmth(moon.get("dignity", ""))
    ad_lord = _current_ad_lord(pc)
    duty_season = ad_lord in ("Saturn", "Sun", "Ketu")
    body = (
        f"With your father — and the older men who shaped you — the bond reads as {fb} one; "
        f"respect and staying in regular touch matter to him more than grand gestures. "
        f"With your mother, and the women who raised or guided you, the tie is {mb} one, "
        "built out of everyday care and old emotional memory. "
    )
    if duty_season:
        body += (
            "This particular stretch of life tends to put elders' wellbeing on your plate — "
            "a health scare, a decision, or simply more of your time. Lean in early, keep an eye on "
            "their check-ups, and settle any old misunderstandings while it's easy. You won't regret the visits."
        )
    else:
        body += (
            "There's no storm cloud over the family right now. The kindest thing you can do is the simple thing: "
            "regular calls, a watchful eye on their health, and clearing up small misunderstandings before they harden."
        )
    return body


def _legal_meta(pc: dict) -> tuple[str, str, str]:
    """Returns (body, tone, timing) for legal / disputes / official matters — chart-specific."""
    rec = get_house_lord(pc, 6)
    lh = rec.get("lord_house")
    ad_lord = _current_ad_lord(pc)
    tense = ad_lord in ("Mars", "Saturn", "Rahu", "Ketu") or (isinstance(lh, int) and lh in _DUSTHANA)
    if tense:
        body = (
            "Right now is a time to be genuinely careful with agreements, paperwork and any disagreement that's brewing. "
            "Don't let pride steer a dispute — put everything in writing, keep clean records, and aim for a fair settlement "
            "rather than a drawn-out fight, which tends to cost you more than it ever returns. If a court case or official "
            "matter is unavoidable, have someone competent review it properly before you sign or commit to anything."
        )
        return body, "amber", "Handle with care in this chapter"
    body = (
        "Official and legal matters look fairly settled for you right now — no sign of a draining battle on the horizon. "
        "Keep your important documents in order and read the fine print, and lean towards the clean, quiet agreements "
        "that suit this calmer stretch."
    )
    return body, "blue", "Calm for now"


def _area_card_html(
    title: str,
    lead: str,
    body: str,
    tone: str,
    conf_label: str,
    timing: str,
) -> str:
    feel_txt, feel_cls = _conf_feel(conf_label)
    return f"""
<div class="card {tone}">
  <div class="when">{_e(_friendly_timing(timing))}</div>
  <h3>{_e(title)}</h3>
  <p class="body" style="color:var(--muted);font-style:italic;margin-bottom:6px;">{_e(lead)}</p>
  <p class="body">{_e(body)}</p>
  <span class="pill {feel_cls}">{_e(feel_txt)}</span>
</div>"""


def _life_area_cards(by_dom: dict, pc: dict, lctx) -> str:
    """The heart of both reports — every real-life area, one warm card each."""
    order = ["career", "finance", "marriage", "children", "parents",
             "property", "health", "legal", "travel", "spiritual"]
    cards = ""
    for dom in order:
        if dom == "parents":
            cards += _area_card_html(
                LIFE_AREA_TITLE[dom], LIFE_AREA_LEAD[dom],
                _parents_body(pc), "blue", "MODERATE", "An ongoing thread",
            )
            continue
        if dom == "legal":
            body, tone, timing = _legal_meta(pc)
            cards += _area_card_html(
                LIFE_AREA_TITLE[dom], LIFE_AREA_LEAD[dom], body, tone, "MODERATE", timing,
            )
            continue

        cl = by_dom.get(dom)
        if dom == "health":
            cards += _area_card_html(
                LIFE_AREA_TITLE[dom], LIFE_AREA_LEAD[dom],
                _health_insight(pc, cl, lctx),
                _area_tone(dom, cl), (cl.confidence if cl else "MODERATE"),
                (cl.timing if cl and cl.timing else "Now and the near future"),
            )
            continue

        if dom == "spiritual" and not cl:
            continue  # only show if there's something real to say

        cards += _area_card_html(
            LIFE_AREA_TITLE[dom], LIFE_AREA_LEAD.get(dom, ""),
            _domain_insight(dom, pc, cl),
            _area_tone(dom, cl), (cl.confidence if cl else "MODERATE"),
            (cl.timing if cl and getattr(cl, "timing", "") else ""),
        )
    return cards


def _short_version(by_dom: dict, pc: dict) -> str:
    """A 'tell me in two lines' opener, in everyday language."""
    parts: list[str] = []
    if by_dom.get("career"):
        parts.append("your work and reputation are a central thread")
    if by_dom.get("finance"):
        parts.append("money grows best through steady, earned effort rather than gambles")
    if by_dom.get("marriage"):
        parts.append("close relationships reward honest, everyday attention")
    if by_dom.get("health"):
        parts.append("your health holds up well on routine, not heroics")
    core = ", ".join(parts) if parts else "you're moving through a steady, preparation-style season of life"
    return (
        f"In plain words: {core}. The pages below walk through your life the way you actually live it — "
        "one area at a time, with the kind of timing you can plan around."
    )


def render_focus_report(
    pc: dict,
    clusters: list[Cluster],
    signals: list[Signal],
    engine: SemanticEngine,
    slug: str,
    focus_domain: str,
    question: str,
    main_q_result: Optional[dict] = None,
) -> str:
    """Detailed single-domain confluence — all techniques, remedies when applicable."""
    meta = pc["meta"]
    nm = _e(meta["client"])
    today = datetime.today()
    title = DOMAIN_TITLE.get(focus_domain, focus_domain.title())
    dom_signals = [s for s in signals if s.domain == focus_domain]
    if not dom_signals:
        for s in signals:
            if engine.assign_domain(s.text) == focus_domain:
                s.domain = focus_domain
                dom_signals.append(s)

    systems = sorted({s.system for s in dom_signals})
    pos = sum(1 for s in dom_signals if s.direction == "positive")
    cau = sum(1 for s in dom_signals if s.direction == "caution")
    direction = "positive" if pos >= cau else ("caution" if cau > pos else "neutral")
    conf = _conf_label(len(systems)) if systems else "SPECULATIVE"

    by_dom: dict[str, Cluster] = {}
    for cl in clusters:
        if cl.domain not in by_dom or cl.score > by_dom[cl.domain].score:
            by_dom[cl.domain] = cl
    top = by_dom.get(focus_domain)
    if top:
        affirmation = top.affirmation
        timing = top.timing
        direction = top.direction
        conf = top.confidence
    else:
        embs = engine.model.encode([s.text for s in dom_signals], normalize_embeddings=True) if dom_signals else None
        centroid = np.mean(embs, axis=0) if embs is not None and len(dom_signals) else None
        if centroid is not None:
            centroid = centroid / (np.linalg.norm(centroid) + 1e-9)
            affirmation = engine._pick_line(focus_domain, direction, centroid, "")
        else:
            affirmation = BOOK_LINES.get(focus_domain, BOOK_LINES["career"]).get("neutral", [""])[0]
        timing = next((s.timing for s in dom_signals if s.timing), "")

    rows = _domain_signal_rows(dom_signals, focus_domain) or (
        f"<tr><td colspan='4'>No lane signals tagged to {title} — re-run after all reports complete.</td></tr>"
    )

    sub_clusters = [c for c in clusters if c.domain == focus_domain and len(c.systems) >= 2]
    sub_html = ""
    for sc in sub_clusters[:5]:
        sub_html += f'<div class="callout {"green" if sc.direction == "positive" else "amber"}"><strong>{len(sc.systems)} methods align:</strong> {_e(sc.affirmation)}</div>'

    remedy_ctx = _remedy_context(pc)
    focus_blocks = _fill_remedy_templates(DOMAIN_FOCUS_REMEDIES.get(focus_domain, []), remedy_ctx)
    psych_html = ""
    if focus_blocks:
        for rtitle, rbody in focus_blocks:
            label = "(supportive)" if direction not in ("caution", "neutral") and cau < pos else ""
            psych_html += f'<div class="remedy-box"><h4>{_e(rtitle)} {label}</h4><p>{_e(rbody)}</p></div>'
    else:
        for rtitle, rbody in _build_remedy_blocks(pc)[:2]:
            psych_html += f'<div class="remedy-box"><h4>{_e(rtitle)}</h4><p>{_e(rbody)}</p></div>'
    remedy_html = _gemstone_and_remedy_html(
        pc, question=question, domain=focus_domain, include_psych=False,
    )
    if psych_html:
        remedy_html += f'<div class="remedy-psych" style="margin-top:16px"><h3 style="font-size:1rem;margin-bottom:8px">Behavioural support</h3>{psych_html}</div>'

    callout_cls = "green" if direction == "positive" else ("red" if direction == "caution" else "amber")
    vim = pc["vimshottari"]
    md = vim["current_md"]["md_lord"]
    ad = next((a for a in vim["current_md_antardashas"] if a.get("status") == "current"), {})

    live_q_html = ""
    if main_q_result and main_q_result.get("ok"):
        try:
            from main_question_report import render_main_question_embed_html
            embed = render_main_question_embed_html(main_q_result, skip_remedy=True)
            if embed.strip():
                live_q_html = f"""<section class="section">
  <h2>Live Chart Techniques (Main Question Engine)</h2>
  {embed}
</section>"""
            syn = main_q_result.get("verdict") or main_q_result.get("synthesis", {})
            if syn.get("confirmed") or syn.get("confirmed_gate"):
                direction = "positive" if syn.get("positive_votes", 0) >= syn.get("caution_votes", 0) else direction
                conf = syn.get("practical_confidence") or syn.get("confidence", conf)
                affirmation = syn.get("headline", affirmation)
                if syn.get("timing") or (syn.get("peak_window") or {}).get("range_label"):
                    timing = syn.get("timing") or syn["peak_window"]["range_label"]
        except Exception:
            pass

    body = f"""
<div class="page">
<div class="rpt-header">
  <h1>Focused Confluence — {title}</h1>
  <div class="sub">Your question · every technique · one clear answer — {nm}</div>
  <div class="meta">
    <span>Question: &ldquo;{_e(question)}&rdquo;</span>
    <span>Focus: {title}</span>
    <span>Methods consulted: {len(systems)}</span>
    <span>Report: {_long_date(today)}</span>
  </div>
</div>

<section class="section">
  <h2>Your Question</h2>
  <blockquote>&ldquo;{_e(question)}&rdquo;</blockquote>
  <p>Semantic analysis mapped this to <strong>{title}</strong> — the same domain routing used for horary questions, applied across your full birth-chart report set.</p>
</section>

<section class="section">
  <h2>Verdict</h2>
  <div class="callout {callout_cls}">
    <strong>{title.upper()} — {_conf_plain(len(systems), conf)}</strong>
    {_e(affirmation)}
    {(' <em>Key window: ' + _e(timing) + '.</em>') if timing else ''}
  </div>
  <p style="font-size:.88rem;color:var(--muted);margin-top:10px">
    Current dasha context: {md}–{ad.get('ad_lord', '')} — sub-period themes are folded into the table below.</p>
</section>

{live_q_html}

<section class="section">
  <h2>Every Method — What It Says About {title}</h2>
  <table><thead><tr><th>Method</th><th>Agrees</th><th>Statement (plain English)</th><th>Timing</th></tr></thead>
  <tbody>{rows}</tbody></table>
</section>

{f'<section class="section"><h2>Semantic Sub-clusters</h2>{sub_html}</section>' if sub_html else ''}

<section class="section">
  <h2>Remedies &amp; Practical Support</h2>
  <p style="font-size:.88rem;color:var(--muted);margin-bottom:12px">Book-backed suggestions for this life area — practice consistently, not once.</p>
  {remedy_html or '<p>No specific remedy flagged; maintain general chart hygiene (sleep, clarity, honest paperwork).</p>'}
</section>

<section class="section">
  <h2>What To Do Next</h2>
  <ul style="margin-left:20px;line-height:1.75">
    <li>Read the affirmative verdict above as your primary guidance — not raw planet tables.</li>
    <li>Cross-check timing against the full confluence roadmap in your main report.</li>
    <li>Send dated life events to calibrate windows; the same question can be re-run sharper.</li>
  </ul>
</section>

<div class="footer">
  <p>Full multi-domain report: Vedic_Confluence_{slug}_*.html</p>
</div>
</div>"""

    dom_slug = focus_domain.replace(" ", "_").title()
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Focus — {title} — {nm}</title>
<style>{_css_confluence()}</style></head><body>{body}</body></html>"""


def render_confluence(
    pc: dict,
    clusters: list[Cluster],
    slug: str,
    signals: list[Signal],
    engine: SemanticEngine,
    *,
    focus_domain: Optional[str] = None,
    question: str = "",
    extracted_path: str = "",
    client_name: str = "",
    dob: str = "",
    lane_count: int = 0,
) -> str:
    meta = pc["meta"]
    nm = _e(client_name or meta.get("client") or slug)
    today = datetime.today()
    vim = pc["vimshottari"]
    md = vim["current_md"]["md_lord"]
    ad = next((a for a in vim["current_md_antardashas"] if a.get("status") == "current"), {})
    ad_lord = ad.get("ad_lord", "")
    ad_rng = f"{_parse_date_short(ad.get('start',''))} – {_parse_date_short(ad.get('end',''))}"
    n_sys = len({s.system for s in signals})

    by_dom: dict[str, Cluster] = {}
    for cl in clusters:
        if cl.domain not in by_dom or cl.score > by_dom[cl.domain].score:
            by_dom[cl.domain] = cl

    lane_banner = ""
    if lane_count < MIN_LANES_FOR_MODERATE:
        lane_banner = f"""
<div class="uncal-banner" style="background:#fdecea;border-left:4px solid #c62828;padding:12px 18px;margin-bottom:18px;border-radius:8px;font-size:.9rem;">
<strong>Partial pass:</strong> {lane_count}/{CORE_LANE_COUNT} specialist sub-reports were on disk when this confluence ran.
Cross-method confidence is capped at MODERATE until the full lane set is generated for <em>{_e(slug)}</em>.
</div>"""

    # ── Per-domain technical confluence: every method, what it says, timing, vote ──
    domain_sections = ""
    for dom in DOMAINS:
        if dom in ("personality", "current"):
            continue
        top = by_dom.get(dom)
        if not top:
            continue
        sys_map = _signals_by_system(signals, dom)
        rows = ""
        for sysname in sorted(sys_map.keys()):
            sig = sys_map[sysname]
            stmt = _snippet(sig.text)
            badge = {"positive": "hi", "caution": "lo", "neutral": "mod"}[sig.direction]
            agree = {"positive": "✔ supports", "caution": "▲ cautions", "neutral": "● neutral"}[sig.direction]
            rows += (f"<tr><td><strong>{_e(sysname)}</strong></td>"
                     f"<td><span class='badge {badge}'>{agree}</span></td>"
                     f"<td>{_e(stmt)}</td><td>{_e(sig.timing if sig.timing else top.timing)}</td></tr>")
        n_methods = len(sys_map) or len(top.systems)
        callout_cls = "green" if top.direction == "positive" else ("red" if top.direction == "caution" else "amber")
        aff_l = (top.affirmation or "").lower()
        if any(x in aff_l for x in ("low risk", "no elevated crisis", "maintenance habits are enough", "no strict mrityu")):
            callout_cls = "green"
        domain_sections += f"""
<section class="section">
  <h2>{DOMAIN_TITLE[dom]}</h2>
  <table class="methods"><thead><tr><th>Method / sub-report</th><th>Verdict</th><th>What it states</th><th>Timing</th></tr></thead>
  <tbody>{rows}</tbody></table>
  <div class="callout {callout_cls}">
    <strong>Confluence verdict — {_conf_plain(n_methods, top.confidence)}.</strong>
    {_e(top.affirmation)}
    {(' <em>Window: ' + _e(top.timing) + '.</em>') if top.timing else ''}
  </div>
</section>"""

    cur_top = by_dom.get("current")
    cur_body = (cur_top.affirmation if cur_top and getattr(cur_top, "affirmation", None)
                else f"Active period: {md} major / {ad_lord} sub ({ad_rng}). A defined band in the verified dasha table.")

    nature = _nature_html(
        engine, signals, pc,
        extracted_path=extracted_path,
        client_name=client_name or meta["client"],
        dob=dob or meta["dob"],
    )
    remedy_html = _gemstone_and_remedy_html(
        pc, question=question or "", domain=focus_domain or "", include_psych=True,
    )
    lctx = build_longevity_context(pc)

    focus_banner = ""
    if focus_domain and question:
        ft = DOMAIN_TITLE.get(focus_domain, focus_domain.title())
        focus_banner = f"""
<div class="uncal-banner" style="background:#e8f2fd;border-left:4px solid #1e5fa8;padding:12px 18px;margin-bottom:22px;border-radius:8px;font-size:.9rem;">
<strong>Client question routed to → {ft}.</strong> A dedicated focus report drills every technique for this area
(<em>Vedic_Focus_{focus_domain.title()}_{slug}_*.html</em>). The plain-language take is in <em>user_report_{slug.lower()}.html</em>.
</div>"""

    body = f"""
<div class="page">
<div class="uncal-banner" style="background:#fff8e1;border-left:4px solid #f9a825;padding:12px 18px;margin-bottom:22px;border-radius:8px;font-size:.9rem;">
<strong>Technical confluence.</strong> {n_sys} independent techniques were read and cross-checked. Where several agree, confidence rises.
This is the analyst view — the plain-language version for the client is <em>user_report_{slug.lower()}.html</em>.
</div>
{lane_banner}
{focus_banner}
<div class="rpt-header">
  <h1>The Confluence Report</h1>
  <div class="sub">All systems cross-checked · one reconciled answer — {nm}</div>
  <div class="meta">
    <span>DOB: {meta['dob']}</span>
    <span>Lagna: {meta.get('lagna_sign','')} · Lord: {meta.get('lagna_lord','')}</span>
    <span>Dasha: {md}–{ad_lord} ({ad_rng})</span>
    <span>Methods read: {n_sys}</span>
    <span>Report: {_long_date(today)}</span>
  </div>
</div>

<section class="section">
  <h2>How To Read This Report</h2>
  <p>Each specialist sub-report (Vimshottari, KP, Jaimini, Ashtakavarga, BNN, Bhardwaj, Yogini, Longevity, RTVD, Numerology, Pillar, Palmistry…) contributes statements about your life. Statements that mean the same thing are grouped, and when several independent methods agree the confluence verdict gains confidence. Each life-area table below shows exactly which method said what, and how the votes reconcile.</p>
</section>

<section class="section">
  <h2>Character &amp; Personality</h2>
  <div class="nature-box" style="background:#faf8ff;border-radius:8px;padding:14px 18px;">{nature}</div>
</section>

<section class="section">
  <h2>Where You Stand Now — {md}–{ad_lord}</h2>
  <div class="callout gold"><strong>Current sub-period ({ad_rng}):</strong> {_e(cur_body)}</div>
</section>

{domain_sections}

<section class="section">
  <h2>Health &amp; Longevity</h2>
  {health_section_html(pc, lctx)}
</section>

<section class="section">
  <h2>Year-by-Year Road Map (active sub-periods)</h2>
  <p style="font-size:.85rem;margin-bottom:12px;color:var(--muted);">Traffic lights track the antardashas crossed with each domain's cross-method vote.</p>
  <div style="overflow-x:auto;">
  <table class="methods">
    <thead><tr>
      <th>Window</th><th>Sub-period</th>
      <th style="text-align:center">Career</th><th style="text-align:center">Finance</th>
      <th style="text-align:center">Health</th><th style="text-align:center">Family</th>
      <th style="text-align:center">Travel</th><th>Key theme</th>
    </tr></thead>
    <tbody>{_roadmap_detail_rows(pc)}</tbody>
  </table>
  </div>
</section>

<section class="section">
  <h2>Top Challenges — Preparation Guide</h2>
  {_build_challenge_boxes(pc)}
</section>

<section class="section">
  <h2>Remedies — Chart-Targeted</h2>
  {remedy_html}
</section>

<section class="section">
  <h2>Confidence Dashboard</h2>
  <div class="conf-dash">
    {''.join(f'<div class="conf-row"><span class="dom">{DOMAIN_TITLE.get(c.domain,c.domain)}</span><span class="votes">{c.confidence} · {len(c.systems)} methods</span></div>' for c in sorted(by_dom.values(), key=lambda x: -x.score)[:12])}
  </div>
</section>

<div class="footer">
  <p>Plain-language client edition: user_report_{slug.lower()}.html</p>
</div>
</div>"""
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Confluence Report — {nm}</title>
<style>{_css_confluence()}</style></head><body>{body}</body></html>"""


def render_user_report(
    pc: dict,
    clusters: list[Cluster],
    slug: str,
    signals: list[Signal],
    engine: SemanticEngine,
    *,
    focus_domain: Optional[str] = None,
    question: str = "",
    extracted_path: str = "",
    client_name: str = "",
    dob: str = "",
    lane_count: int = 0,
    main_q_result: Optional[dict] = None,
) -> str:
    meta = pc["meta"]
    nm = _e(client_name or meta.get("client") or slug)
    dob_fmt = meta["dob"]
    d = _parse_dob(meta["dob"])
    if d:
        dob_fmt = _long_date(d)
    today = datetime.today()
    vim = pc["vimshottari"]
    ad = next((a for a in vim["current_md_antardashas"] if a.get("status") == "current"), {})
    ad_rng = f"{_parse_date_short(ad.get('start',''))} – {_parse_date_short(ad.get('end',''))}"

    by_dom: dict[str, Cluster] = {}
    for cl in clusters:
        if cl.domain not in by_dom or cl.score > by_dom[cl.domain].score:
            by_dom[cl.domain] = cl

    def best(dom):
        return by_dom.get(dom)

    lctx = build_longevity_context(pc)

    nature = _nature_html(
        engine, signals, pc,
        extracted_path=extracted_path,
        client_name=client_name or meta["client"],
        dob=dob or meta["dob"],
    )

    cur = best("current")
    ad_lord = ad.get("ad_lord", "")
    cur_title = {
        "Ketu": "A quiet, clear-the-decks season",
        "Venus": "Warmth, comfort and steady gains",
        "Mercury": "Deals, learning and getting things done",
        "Saturn": "Hard work, duty and laying foundations",
        "Mars": "Drive and energy — pace yourself",
        "Jupiter": "Growth, learning and good counsel",
        "Sun": "Stepping into the spotlight",
        "Moon": "Home, family and emotional rhythm",
        "Rahu": "Ambition and new networks",
    }.get(ad_lord, "An active chapter of your life")
    cur_body = _current_season_text(pc)
    cur_extra = {
        "Ketu": "It's a good time to let go of what's run its course and quietly sharpen your skills — what you prepare now feeds the busier years that follow.",
        "Venus": "Money, ease at home and a little recognition can rise together — act deliberately and enjoy it.",
        "Mercury": "Read the fine print, finish what's open, and you'll be surprised how much gets done.",
        "Saturn": "Progress comes through patience and showing up. It's slower, but what you build now lasts.",
        "Mars": "Plenty of fire and drive — channel it into clear goals and guard your rest so you don't burn out.",
    }.get(ad_lord, "Line up your daily effort with what this season rewards, and don't force what isn't ready yet.")
    right_now = _area_card_html(
        "Where life stands today",
        f"Roughly {ad_rng}.",
        f"{cur_body} {cur_extra}",
        "amber",
        cur.confidence if cur else "MODERATE",
        ad_rng,
    )

    health_block = health_section_html(pc, lctx, cluster_text="")

    focus_section = ""
    if question.strip():
        if main_q_result and main_q_result.get("ok"):
            v = main_q_result.get("verdict") or {}
            mq_conf = _cap_confidence(
                str(v.get("practical_confidence", "MODERATE")).replace("-", " ").upper(),
                lane_count,
                speculative=False,
            )
            qbody = " ".join(x for x in [v.get("headline", ""), v.get("subhead", "")] if x)
            peak = (v.get("peak_window") or {}).get("range_label", "")
            if peak:
                qbody += f" The most favourable stretch looks like {peak}."
            focus_section = _area_card_html(
                "Your question, answered directly",
                f'You asked: "{question}"',
                qbody,
                "blue", mq_conf, peak or "See below",
            )
        elif focus_domain:
            fcl = best(focus_domain)
            if fcl:
                focus_section = _area_card_html(
                    "Your question, answered directly",
                    f'You asked: "{question}"',
                    _domain_insight(focus_domain, pc, fcl),
                    "blue", fcl.confidence, fcl.timing or "",
                )

    body = f"""
<div class="wrap">
<div class="hero">
  <h1>Your Life, In Plain Words</h1>
  <div class="tag">A warm, honest look at the things that actually shape your days</div>
  <div class="meta">
    <span>{nm}</span>
    <span>Born {_e(dob_fmt)}</span>
    <span>Prepared {_long_date(today)}</span>
  </div>
</div>

<div class="note">This reading looks at your life the way you live it — your work, your money, the people you love, your health, your home and the worries that keep you up at night. It's meant to be read like a letter, not a chart. If you ever share a few real dates from your life (a marriage, a move, a job change, an illness), the timing below only gets sharper.</div>

{focus_section}

<div class="section-h">The Short Version</div>
<div class="card blue"><p class="body">{_e(_short_version(by_dom, pc))}</p></div>

<div class="section-h">Who You Are</div>
<div class="card blue">{nature}</div>

<div class="section-h">Where Life Stands Today</div>
{right_now}

<div class="section-h">Your Life, Area by Area</div>
{_life_area_cards(by_dom, pc, lctx)}

{health_block}

{traffic_light_html(pc, lctx)}

{remedies_html(pc, lctx, question=question, domain=focus_domain or "")}

<div class="section-h">A Gentle Note</div>
<div class="card">
  <p class="body">Think of this as a thoughtful letter about your life — something to reflect on, not a rule book.
  It isn't a substitute for a doctor, a lawyer or a financial adviser, and nothing here predicts the timing of anything as serious as death.
  Where you see talk of "watch your health," read it as a friendly nudge to rest and get a check-up — never as a warning to be afraid of.</p>
</div>

<div class="footer">
  <p>Prepared with care on {_long_date(today)} · for {nm}</p>
</div>
</div>"""
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Your Life Report - {nm}</title>
<style>{_css_user()}</style></head><body>{body}</body></html>"""


def _apply_confidence_caps(clusters: list[Cluster], lane_count: int) -> None:
    for cl in clusters:
        cl.confidence = _cap_confidence(
            cl.confidence,
            lane_count,
            speculative=_is_speculative_affirmation(cl.affirmation),
        )


def generate_confluence_reports(
    extracted_path: str,
    reports_dir: str,
    client_name: str,
    dob: str,
    slug: str,
    *,
    client_question: str = "",
    palm_analysis: Optional[dict] = None,
    precomputed_path: Optional[str] = None,
    birth_time: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    timezone: Optional[float] = None,
    place_name: str = "",
    ayanamsa: str = "LAHIRI",
    gender: int = 0,
) -> tuple[str, str, Optional[str], dict]:
    pc = resolve_precompute(
        client_name, dob,
        extracted_path=extracted_path or None,
        precomputed_path=precomputed_path,
        birth_time=birth_time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        place_name=place_name,
        ayanamsa=ayanamsa,
    )
    from chart_identity import assert_chart_identity, sync_display_name

    assert_chart_identity(pc, client_name=client_name, dob=dob, slug=slug)
    sync_display_name(pc, client_name)

    rdir = Path(reports_dir)
    lane_count = _count_lane_files(rdir, slug)
    signals = _signals_from_precompute(pc)
    lane_sigs, collector_systems = _signals_from_lane_collectors(
        extracted_path, client_name, dob, pc,
    )
    signals.extend(lane_sigs)
    skip_html = collector_systems
    signals.extend(_extract_html_signals(rdir, slug, skip_systems=skip_html))
    signals.extend(_signals_from_palm(palm_analysis))
    signals = _clean_signals(signals)
    for sig in signals:
        if sig.domain == "unknown":
            pass  # assigned in cluster_signals
    engine = SemanticEngine()
    focus_domain = detect_focus_domain(client_question, engine)
    clusters = engine.cluster_signals(signals)
    _apply_confidence_caps(clusters, lane_count)

    main_q_result = None
    if client_question.strip() and birth_time:
        try:
            from main_question_report import SubjectInput, build_main_question_report
            main_q_result = build_main_question_report(
                client_question.strip(),
                SubjectInput(
                    name=client_name, dob=dob, birth_time=birth_time,
                    latitude=latitude or 0.0, longitude=longitude or 0.0,
                    timezone=timezone if timezone is not None else 5.5,
                    place_name=place_name, gender=gender,
                    extracted_path=extracted_path or "",
                    precomputed_path=precomputed_path or "",
                ),
            )
        except Exception:
            main_q_result = None

    conf_html = render_confluence(
        pc, clusters, slug, signals, engine,
        focus_domain=focus_domain, question=client_question,
        extracted_path=extracted_path,
        client_name=client_name,
        dob=dob,
        lane_count=lane_count,
    )
    user_html = render_user_report(
        pc, clusters, slug, signals, engine,
        focus_domain=focus_domain, question=client_question,
        extracted_path=extracted_path,
        client_name=client_name,
        dob=dob,
        lane_count=lane_count,
        main_q_result=main_q_result,
    )
    focus_html: Optional[str] = None
    if focus_domain and client_question.strip():
        focus_html = render_focus_report(
            pc, clusters, signals, engine, slug, focus_domain, client_question.strip(),
            main_q_result=main_q_result,
        )
    summary = {
        "signals": len(signals),
        "clusters": len(clusters),
        "focus_domain": focus_domain or "",
        "lane_count": lane_count,
        "lane_total": CORE_LANE_COUNT,
        "identity_ok": True,
        "top_career_conf": best.confidence if (best := max([c for c in clusters if c.domain == "career"], key=lambda x: x.score, default=None) or Cluster("career", "neutral", "", [], [])) else "—",
    }
    try:
        from gemstone_remedy import build_remedy_report, save_remedy_report
        remedy_report = build_remedy_report(
            pc, question=client_question, domain=focus_domain or "",
            client_name=client_name,
        )
        remedy_path = save_remedy_report(remedy_report, reports_dir, slug)
        if remedy_path:
            summary["remedy_path"] = remedy_path
    except Exception:
        pass
    return conf_html, user_html, focus_html, summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Semantic confluence + user report (no LLM)")
    ap.add_argument("extracted")
    ap.add_argument("reports_dir", help="folder with Vedic_* lane HTML files")
    ap.add_argument("name")
    ap.add_argument("dob")
    ap.add_argument("--slug", default=None)
    add_chart_source_args(ap)
    ap.add_argument("--question", default="", help="Optional client focus question")
    ap.add_argument("-o", "--out-dir", default=None)
    args = ap.parse_args()
    slug = args.slug or args.name.replace(" ", "_")
    out_dir = Path(args.out_dir) if args.out_dir else Path(args.reports_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().strftime("%Y%m%d")
    kw = chart_kwargs_from_args(args)
    conf, user, focus, summary = generate_confluence_reports(
        args.extracted, args.reports_dir, args.name, args.dob, slug,
        client_question=args.question,
        **kw,
    )
    cp = out_dir / f"Vedic_Confluence_{slug}_{today}.html"
    up = out_dir / f"user_report_{slug.lower()}.html"
    cp.write_text(conf, encoding="utf-8")
    up.write_text(user, encoding="utf-8")
    print(f"signals={summary['signals']} clusters={summary['clusters']} focus={summary.get('focus_domain','')} career_conf={summary['top_career_conf']}")
    print(f"written → {cp}")
    print(f"written → {up}")
    if focus and summary.get("focus_domain"):
        fp = out_dir / f"Vedic_Focus_{summary['focus_domain'].title()}_{slug}_{today}.html"
        fp.write_text(focus, encoding="utf-8")
        print(f"written → {fp}")


if __name__ == "__main__":
    main()
