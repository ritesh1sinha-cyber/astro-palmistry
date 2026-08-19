"""
Confluence life-aspect reading.

A human palmist does not read a palm feature-by-feature; they read the
*confluence* of several features for each area of life (health, mind, love,
career, wealth, travel, character, fortune). This module encodes those
combination rules from the book corpus and produces one synthesized,
second-person paragraph per life aspect, with the book lines that back it.

Each rule fires on the dominant hand (current, lived life). When the same
combination also holds on the non-dominant hand it is "reinforced" — the
classic confluence weighting (both hands agree = stable, dependable trait).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from palm_api.report_format import book_label

# ---- ordered life aspects (titles shown in the report) ---------------------
ASPECTS: list[tuple[str, str]] = [
    ("career", "Work & Career"),
    ("wealth", "Money & Resources"),
    ("love", "Relationships & Emotions"),
    ("health", "Health & Vitality"),
    ("travel", "Travel, Change & Imagination"),
    ("character", "Personal Growth & Direction"),
]

# Authentic Domain-Specific Vedic Astrological Upayas
_ASPECT_VEDIC_UPAYAS: dict[str, dict[str, str]] = {
    "career": {
        "planet": "Saturn & Sun (Shani-Surya)",
        "upaya": (
            "<b>Surya Arghya & Shani Beej Mantra</b>: Offer daily Surya Arghya (water with kumkum from a pure copper vessel) "
            "at sunrise to amplify executive recognition and professional authority. On Saturday evenings, chant "
            "<code>Om Pram Preem Praum Sah Shanaishcharaya Namah</code> (108 times) to turn patient labor into lasting vocational standing."
        ),
    },
    "wealth": {
        "planet": "Mercury & Venus (Budh-Lakshmi)",
        "upaya": (
            "<b>Budh Upasana & Cow Seva</b>: Feed fresh green grass or spinach to cows on Wednesday mornings and keep "
            "a thriving green plant in the Northern sector of your workspace. Chant <code>Om Shreem Hreem Kleem Shreem Namah</code> "
            "or Shree Suktam to fortify liquid cash flow and commercial prosperity."
        ),
    },
    "love": {
        "planet": "Venus & Moon (Shukra-Chandra)",
        "upaya": (
            "<b>Shukra Beej Mantra & Prithvi Mudra</b>: Practice Prithvi Mudra (join thumb tip with ring fingertip) "
            "to ground emotional warmth and deepen interpersonal trust. Chant <code>Om Dram Dreem Draum Sah Shukraya Namah</code> "
            "(108 times on Fridays) and donate white sweets, milk, or rice on Friday mornings for domestic harmony."
        ),
    },
    "health": {
        "planet": "Sun & Mars (Surya-Mangal)",
        "upaya": (
            "<b>Surya Mudra & Gayatri Upasana</b>: Practice Surya Mudra (fold ring finger to touch thumb base) for 10–15 minutes "
            "daily during morning meditation to steady vital energy and focus. Recite the Gayatri Mantra or Aditya Hridaya "
            "Stotram at sunrise to support mental clarity and daily stamina."
        ),
    },
    "travel": {
        "planet": "Moon (Chandra Dev)",
        "upaya": (
            "<b>Prana Mudra & Chandra Upasana</b>: Practice Prana Mudra (join tips of ring and little fingers with thumb tip) "
            "to steady emotional tides and mental restlessness before journeys. Chant <code>Om Shram Shreem Shraum Sah Chandraya Namah</code> "
            "on Monday evenings and drink water stored in a pure silver cup."
        ),
    },
    "character": {
        "planet": "Jupiter & Sun (Guru-Surya)",
        "upaya": (
            "<b>Guru Beej Mantra & Gyan Mudra</b>: Practice Gyan Mudra (join thumb tip with index fingertip) "
            "for 15 minutes daily during morning meditation. Chant the Guru Beej Mantra "
            "<code>Om Gram Greem Graum Sah Gurave Namah</code> (108 times on Thursdays) to channel "
            "leadership authority, strategic wisdom, and dignified self-respect."
        ),
    },
}


class View:
    """Flat, safe accessor over one hand's cleaned features."""

    def __init__(self, feats: dict[str, Any]):
        self.f = feats or {}
        self.lines = self.f.get("lines") or {}
        self.mounts = self.f.get("mounts") or {}
        self.minor = self.f.get("minor_lines") or {}
        self.morph = self.f.get("morphology") or {}
        self.thumb = self.morph.get("thumb") or {}
        self.marks = {
            (m.get("type"), m.get("zone")) for m in (self.f.get("special_marks") or [])
        }
        self.mark_types = {m.get("type") for m in (self.f.get("special_marks") or [])}

    def line(self, k: str) -> dict[str, Any]:
        return self.lines.get(k) or {}

    def has_line(self, k: str) -> bool:
        return bool(self.line(k).get("detected"))

    def lp(self, k: str, p: str) -> Any:
        return self.line(k).get(p)

    def mount(self, k: str) -> str:
        return str(self.mounts.get(k) or "unknown")

    def has_minor(self, k: str) -> bool:
        return bool((self.minor.get(k) or {}).get("detected"))

    def hand_type(self) -> str:
        return str(self.morph.get("hand_type") or "unknown")

    def has_mark(self, mtype: str, zone: str | None = None) -> bool:
        if zone is None:
            return mtype in self.mark_types
        return (mtype, zone) in self.marks


@dataclass
class Rule:
    aspect: str
    cond: Callable[[View], bool]
    text: str
    book: str | None = None
    page: int | None = None
    quote: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)
    # Stable ID used by the modern-correlation layer. The ID is assigned
    # after RULES is built so the existing astrology/palmistry rules remain
    # untouched.
    rule_id: str = ""


def _prom(v: View, m: str) -> bool:
    return v.mount(m) == "prominent"


def _flat(v: View, m: str) -> bool:
    return v.mount(m) == "flat"


# ---------------------------------------------------------------------------
# Confluence rules. `text` is the synthesized, second-person palmist statement;
# `quote` is the verbatim/near-verbatim book line that backs it.
# ---------------------------------------------------------------------------
RULES: list[Rule] = [
    # ---------------- CHARACTER & TEMPERAMENT ----------------
    Rule("character", lambda v: v.hand_type() == "earth",
         "Let me start with the shape of your hand — it's square and solid, what we call an Earth hand. You're the kind of person others lean on: practical, steady, dependable. You trust what you can build with your own two hands far more than big talk or grand promises.",
         "case_studies_modern_50", None, "A heavy, square hand with short thick fingers is very practical, capable, active."),
    Rule("character", lambda v: v.hand_type() == "air",
         "The first thing your hand tells me is that you live in your mind — yours is an Air hand. Ideas, words, people, conversation: that's your oxygen. You think out loud and need to talk things through, and a dull, silent routine quietly drains the life out of you.",
         "case_studies_modern_50", None, ""),
    Rule("character", lambda v: v.hand_type() == "fire",
         "Your hand is a Fire hand — quick, restless, full of life. You act first and think on your feet. When something fires you up you throw your whole self into it, and when something bores you, you simply can't pretend otherwise.",
         "case_studies_modern_50", None, ""),
    Rule("character", lambda v: v.hand_type() == "water",
         "Yours is a Water hand — soft, finely tuned, deeply feeling. You pick up on things before anyone's said a word, and you read a room instantly. Your moods move like weather, and that sensitivity is both your gift and the thing you have to protect.",
         "case_studies_modern_50", None, ""),
    Rule("character", lambda v: v.thumb.get("length") == "long",
         "Now look at your thumb — it's long and firm. That's real willpower. Once you've made up your mind, you don't bend easily, and you like to be the one steering your own life rather than being told where to go.",
         "case_studies_modern_50", 40, "Long thumbs give a strong will."),
    Rule("character", lambda v: v.thumb.get("length") == "short",
         "Your thumb is on the shorter side, and that tells me your heart usually wins the argument with your head. You're a romantic at core — you'd rather feel something is right than be coldly, technically correct about it.",
         "case_studies_modern_50", 40, "Short thumbs show romantics."),
    Rule("character", lambda v: v.thumb.get("opening") == "wide",
         "See how your thumb opens out wide and easy from the hand? You're open-handed — generous with your money, your time, your help. You'd never be the one who quietly 'forgets' their share of the bill.",
         "case_studies_modern_50", 40,
         "The thumb which leans away from the hand when open shows someone who will never dodge paying their round."),
    Rule("character", lambda v: v.thumb.get("opening") == "narrow",
         "You hold your thumb in close to the hand — that's caution. You keep a little of yourself back and watch quietly until people earn your trust. There can be some anxiety behind that guard, so the people who get close to you are well chosen.",
         "case_studies_modern_50", 40, "The tightly held thumb can show an anxious mental framework."),
    Rule("character", lambda v: v.morph.get("index_vs_ring") == "index_longer",
         "Your index finger stands taller than your ring finger, and that's pride and ambition. You want to lead, to be respected, to matter — and taking orders for too long never sits comfortably with you.",
         "secrets_profession_popularity", None, ""),
    Rule("character", lambda v: v.morph.get("index_vs_ring") == "ring_longer",
         "Your ring finger reaches past your index — you may be willing to take calculated risks when achievement or recognition matters more than playing it safe.",
         "secrets_profession_popularity", None, ""),

    # ---------------- MIND & INTELLECT ----------------
    Rule("mind", lambda v: v.lp("head", "start_relation") in ("separated", "separated_wide"),
         "Look at where your head line starts — it pulls away from your life line. You were your own person early in life. You make your own calls and don't wait for anyone's permission, though that same independent streak can make you impatient and a touch headstrong.",
         "case_studies_modern_50", 21,
         "If the life line is separated from the head line, this shows someone adventurous, impatient and very independent."),
    Rule("mind", lambda v: v.lp("head", "start_relation") == "merged",
         "Your head and life lines begin joined together. As a youngster you were careful, close to family and slow to push yourself forward — but that confidence to stand on your own two feet is something you've earned with experience.",
         "case_studies_modern_50", 21, ""),
    Rule("mind", lambda v: v.lp("head", "direction") == "moon",
         "Your head line slopes down toward the Moon, and that's a strong imagination. You're pulled toward art, beauty, ideas and the spiritual side of things far more than toward dry facts and cold logic.",
         "case_studies_modern_50", 22,
         "A deeply sloping head line will be seen with imaginative, creative and artistic topics."),
    Rule("mind", lambda v: v.lp("head", "direction") == "straight",
         "Your head line runs straight across — that's a practical, logical mind. You like solid ground under your feet: facts, security, a plan that actually works. You're not easily sold a daydream.",
         "case_studies_modern_50", 22,
         "The straight head line type is more down-to-earth, rational and logical."),
    Rule("mind", lambda v: v.lp("head", "depth") == "deep" and v.thumb.get("length") == "long",
         "Here's a strong combination I can see: a deep head line together with a long, firm thumb. When you set your mind on something, you don't just think about it — you drive it all the way through to the finish.",
         "case_studies_modern_50", 40, "Long thumbs give a strong will; make sure the head line backs it up."),
    Rule("mind", lambda v: _prom(v, "mercury"),
         "The pad below your little finger is full and well-developed. That's a sharp mind for words, business and dealing with people — you think fast, you talk well, and you know how to close a deal.",
         "palmistry_for_all", 124, "Mercury = Mentality, commerce, science."),
    Rule("mind", lambda v: v.has_minor("ring_of_solomon"),
         "There's a Ring of Solomon curving under your index finger — the teacher's and counsellor's mark. People bring you their problems because you understand human nature almost instinctively.",
         "succinct_palmistry", None, ""),

    # ---------------- LOVE, MARRIAGE & EMOTIONS ----------------
    Rule("love", lambda v: v.lp("heart", "depth") == "deep" and _prom(v, "venus"),
         "Your heart line is deep and the mount at the base of your thumb is full — you love with your whole chest. Warm, passionate, openly affectionate. But you need that love returned in the same measure; one-sided affection wounds you quickly.",
         "palmistry_for_all", 124, "Venus = Love, sensuality and passion."),
    Rule("love", lambda v: v.lp("heart", "depth") == "thin" and _flat(v, "venus"),
         "Your heart line is fine and the Venus mount is quiet, so you don't wear your feelings on your sleeve. You're reserved and slow to open up — but make no mistake, the love is real and deep once someone has truly earned your trust.",
         "case_studies_modern_50", 22,
         "A flat Venus mount can show a feeling of lack of maternal support and love during childhood."),
    Rule("love", lambda v: v.lp("heart", "start_zone") == "jupiter",
         "Your heart line begins high, under the index finger — you're an idealist in love. You set the bar high and you want a partner you can genuinely admire and feel proud to stand beside.",
         "case_studies_modern_50", None,
         "Notice if the heart line starts from Jupiter, taking from it ambition, pride and individuality."),
    Rule("love", lambda v: v.lp("heart", "start_zone") == "saturn",
         "Your heart line starts under the middle finger — you love seriously, with a real sense of duty, and a self-protective streak. You don't hand your heart over cheaply, and the right person has to be patient to reach it.",
         "case_studies_modern_50", None, "From Saturn, a more selfish sexuality."),
    Rule("love", lambda v: v.has_minor("girdle_of_venus"),
         "You feel everything intensely in matters of the heart — sensitive and highly strung — and you do best with a calm, steady partner who isn't thrown by the depth of your feeling.",
         "succinct_palmistry", None, ""),
    Rule("love", lambda v: v.has_minor("marriage"),
         "I can see clear union lines on the edge of your hand below the little finger. Significant, committed relationships are written right into your palm — these are the bonds that shape your life.",
         "case_studies_modern_50", None,
         "The marriage line curls onto the Mercury mount; this is really a deep relationship line."),
    Rule("love", lambda v: _prom(v, "venus"),
         "The mount at the base of your thumb is full and warm — that's strong family feeling and a generous heart. You love your people fiercely, and you're not shy about showing it.",
         "palmistry_for_all", 124, "Venus = Love, sensuality and passion."),

    # ---------------- CAREER & DESTINY ----------------
    Rule("career", lambda v: v.has_line("fate") and v.lp("fate", "quality") == "clear" and v.lp("fate", "reach") == "saturn",
         "Your fate line runs clear and unbroken right up the centre of your palm — that's a settled calling. You find your place in the world and climb it steadily, and work rewards you most when you stay the course rather than chop and change.",
         "case_studies_modern_50", 27,
         "A good, unbroken fate line will show good adjustment to one's sphere."),
    Rule("career", lambda v: v.has_line("fate") and v.lp("fate", "quality") == "broken",
         "There's a clear break in your fate line. Expect a real change of direction in your work around that age — and don't fear it. As long as the new stretch begins before the old one ends, it's a step up, not a stumble.",
         "palmistry_for_all", 64,
         "A break in the Fate Line is not always a bad sign, provided that one side begins before the other ends."),
    Rule("career", lambda v: not v.has_line("fate"),
         "You don't carry a strong fate line, and that's not a gap — it means you write your own story. Your path comes from the choices you make, not from being carried along by circumstance or family expectation.",
         "case_studies_modern_50", None, ""),
    Rule("career", lambda v: v.has_minor("sun"),
         "You've got a Sun line — that's talent that gets noticed. There's genuine potential here for recognition, even a measure of fame or public reward, for the work you do.",
         "case_studies_modern_50", None, "The Apollo line will add indications of wealth and recognition."),
    Rule("career", lambda v: _prom(v, "saturn"),
         "The mount under your middle finger is firm — you have the patience and seriousness that long, responsible careers demand. You can carry weight and pressure that would make others buckle.",
         "palmistry_for_all", 124, "Saturn = Reserve, melancholy, seriousness."),
    Rule("career", lambda v: _prom(v, "jupiter"),
         "A full mount under your index finger tells me you're built to lead. You want responsibility, command and recognition, and you'll always feel restless in a role that's too small for you.",
         "palmistry_for_all", 124, "Jupiter = Ambition, power, domination."),

    # ---------------- WEALTH & FORTUNE ----------------
    Rule("wealth", lambda v: v.has_minor("sun") and _prom(v, "mercury"),
         "A Sun line alongside a strong Mercury mount — money comes to you through skill and reputation. Get really good at something, let yourself be known for it, and the income follows. You earn through ability, not luck alone.",
         "succinct_palmistry", None,
         "Good wealth: long Jupiter finger, triangle on Mercury, strong thumb, and a star on the tip of Jupiter."),
    Rule("wealth", lambda v: v.has_mark("trident"),
         "There's a trident in your palm — almost as fortunate as a star. Wherever it sits, it pushes that part of your life toward real success, recognition and prosperity. It's a mark I'm always glad to see.",
         "succinct_palmistry", None,
         "A trident is nearly as good a marking as a star, indicating celebrity and wealth."),
    Rule("wealth", lambda v: v.has_mark("star", "jupiter"),
         "A star sits on your Jupiter mount — one of the truly lucky ones. It points to ambition fulfilled and a real rise in your standing in life.",
         "succinct_palmistry", None, "A star on Jupiter Mount: increase of fortune."),
    Rule("wealth", lambda v: v.has_mark("triangle") or v.has_mark("square"),
         "You carry a triangle or square in your palm — the planner's mark. You think before you leap, and it pays off: your ventures tend to work out and your losses stay contained. You're rarely caught off guard.",
         "principles_self_learning", 32,
         "A positive sign (triangle, square and fish) means that planning gives positive results to you."),
    Rule("wealth", lambda v: v.has_line("fate") and v.lp("fate", "reach") == "saturn" and v.has_minor("sun"),
         "Your fate line completes high on the palm and you've got a Sun line to go with it — that's the classic prosperity pairing. Steady status, and the reward to match it.",
         "case_studies_modern_50", 27, ""),

    # ---------------- HEALTH & VITALITY ----------------
    Rule("health", lambda v: v.lp("life", "depth") == "deep" and _prom(v, "venus"),
         "Your life line is deep and the mount beside it is full — you've got a strong constitution. You recover quickly, you bounce back from setbacks, and you carry real physical warmth and energy through life.",
         "case_studies_modern_50", 22, "The wider the curve covering the life line, the better."),
    Rule("health", lambda v: v.lp("life", "depth") == "deep" and _prom(v, "mars"),
         "A deep life line backed by a firm Mars mount — that's stamina and fight in you. Illness has a hard time keeping you down for long; you heal up and get back on your feet.",
         "palmistry_for_all", 124, "Mars = Vitality, courage, fighting."),
    Rule("health", lambda v: v.lp("life", "depth") == "thin" or v.lp("life", "sweep") == "close_to_thumb",
         "Your life line is fine and hugs close to the thumb — your constitution is on the sensitive side. This isn't a warning, it's an instruction: pace yourself, guard your sleep, and don't run yourself into the ground, because you feel it faster than most.",
         "case_studies_modern_50", 22,
         "Where the curve is non-existent, it infers poor resistance to illness and lacking immune function."),
    Rule("health", lambda v: v.has_minor("mercury"),
         "You have a Health line — think of it as a dashboard light for your stomach and your nerves. When life gets stressful, that's where you'll feel it first, so let it be your early warning to slow down.",
         "case_studies_modern_50", None,
         "The health line is seen going up diagonally toward the Mercury finger."),
    Rule("health", lambda v: v.lp("life", "depth") == "deep",
         "Your life line is deep and strong — a solid life force underneath everything. Good baseline energy and resilience to build the rest of your health on.",
         "case_studies_modern_50", None, ""),

    # ---------------- TRAVEL, CHANGE & IMAGINATION ----------------
    Rule("travel", lambda v: _prom(v, "moon") and v.has_minor("travel"),
         "A full Moon mount together with travel lines — you're a genuine wanderer at heart. Journeys, moving home, foreign places and water all draw you, and you come most alive when you're away from the familiar.",
         "palmistry_for_all", 124, "Moon = Imagination, romance, changeability."),
    Rule("travel", lambda v: _prom(v, "moon"),
         "Your Moon mount is full — a strong imagination and a restless heart. You're forever pulled toward new horizons, and too much sameness makes you itch for a change of scene.",
         "palmistry_for_all", 124, "Moon = Imagination, romance, changeability."),
    Rule("travel", lambda v: v.has_minor("travel"),
         "There are travel lines in your palm — journeys and moves that genuinely matter in your story, not just the odd holiday. Movement is woven into your life.",
         "succinct_palmistry", None, ""),
    Rule("travel", lambda v: v.has_mark("star", "moon"),
         "Take a little extra care on long trips and around water — but read it the right way, because it also marks a vivid intuition that you should learn to trust.",
         "succinct_palmistry", None, "A star on Moon Mount: travels, danger of accident, psychic breakthrough."),

    # ---------------- SPECIAL MARKS & DESTINY ----------------
    Rule("fortune", lambda v: v.has_mark("star", "jupiter"),
         "A star on Jupiter — among the luckiest marks a hand can carry. It speaks of big ambition that actually comes good, and a real lift in your fortunes along the way.",
         "succinct_palmistry", None, "A star on Jupiter Mount: increase of fortune."),
    Rule("fortune", lambda v: v.has_mark("star", "venus"),
         "There's a star sitting high on your Venus mount — a romantic and fortunate sign. Love tends to go your way more often than not.",
         "succinct_palmistry", None, "A star on Venus Mount: high on mount — romantic, success."),
    Rule("fortune", lambda v: v.has_mark("trident"),
         "A trident in your palm strongly boosts the luck and success of wherever it falls — it's one of the most auspicious marks you can carry, and you have it.",
         "succinct_palmistry", None, "A trident indicates celebrity and wealth."),
    Rule("fortune", lambda v: v.has_mark("cross", "saturn"),
         "A cross under your middle finger points to a karmic test around duty and responsibility. When it arrives, meet it with patience rather than force.",
         "palmistry_for_all", 66,
         "A cross found on the Fate Line and on the Mount of Saturn marks a fated turning point."),
    Rule("fortune", lambda v: v.has_mark("grille"),
         "Energy scatters when you're restless or pulled in too many directions. Pick your focus and channel it on purpose, or it leaks away.",
         "succinct_palmistry", None, "The grille shows energy scattered through restlessness."),
    Rule("fortune", lambda v: v.has_mark("triangle"),
         "A triangle here is mental skill applied well — a constructive, fortunate mark. You have a way of thinking your path through to a good outcome.",
         "principles_self_learning", 32, "A positive sign (triangle, square and fish) gives positive results."),
]

# Stable IDs for the 50 existing confluence rules. Keeping IDs separate from
# the rule text lets the human-correlation layer evolve without rewriting the
# underlying palmistry evidence rules.
for _idx, _rule in enumerate(RULES, 1):
    _rule.rule_id = f"R{_idx:02d}_{_rule.aspect}"


def _calculate_confluence_verdict(
    akey: str,
    points: list[dict[str, Any]],
    quality_grade: str,
    dv: Optional[View] = None,
    nv: Optional[View] = None,
) -> dict[str, Any]:
    supporting_signals: list[str] = []
    conflicting_signals: list[str] = []
    score = 0
    reinforced_count = 0

    for p in points:
        txt = str(p.get("traditional_meaning") or p.get("text") or "").strip()
        both = bool(p.get("reinforced"))
        if both:
            reinforced_count += 1
            score += 1
            hand_badge = "in both hands (High confidence)"
        else:
            hand_badge = "on active hand (Moderate confidence)"

        txt_l = txt.lower()
        if any(w in txt_l for w in ("deep", "clear", "prominent", "trident", "triangle", "square", "star", "well-formed")):
            score += 2
            supporting_signals.append(f"{txt} · {hand_badge}")
        elif any(w in txt_l for w in ("grille", "cross", "island", "broken", "wavy", "caution", "restless", "delicate", "sensitive")):
            score -= 2
            conflicting_signals.append(f"{txt} · {hand_badge}")
        else:
            score += 1
            supporting_signals.append(f"{txt} · {hand_badge}")

    # Check for fine marks on mounts
    if dv:
        if akey in ("career", "character") and dv.has_mark("grille", "jupiter"):
            if not any("grille" in s.lower() for s in conflicting_signals):
                conflicting_signals.append("Grille on Jupiter mount (Scattered energy when too many priorities compete)")
                score -= 2
        if akey in ("career", "character") and dv.has_mark("trident", "jupiter"):
            if not any("trident" in s.lower() for s in supporting_signals):
                supporting_signals.append("Trident on Jupiter mount (Leadership ambition and recognition)")
                score += 2

    # Image quality gating
    if quality_grade == "poor":
        score -= 2
        confidence = "Tentative"
        conflicting_signals.append("Photograph grade is poor — fine line markings cannot be resolved with certainty")
    elif quality_grade == "fair":
        score -= 1
        confidence = "Moderate"
        conflicting_signals.append("Photograph grade is fair — timing windows widened to avoid false precision")
    else:
        confidence = "High" if reinforced_count >= 1 else "Moderate"

    # Multi-dimensional verdict determination
    if akey == "career":
        if supporting_signals and conflicting_signals:
            verdict = "Good with pressure"
        elif score >= 3:
            verdict = "Strong & Supportive"
        elif score >= 1:
            verdict = "Moderate / Developing"
        else:
            verdict = "Demanding / Needs Focus"
    elif akey == "wealth":
        if score >= 3 and not conflicting_signals:
            verdict = "Strong / Favourable"
        elif score >= 1:
            verdict = "Moderate / Improving"
        else:
            verdict = "Delicate / Needs Discipline"
    elif akey == "love":
        if supporting_signals and conflicting_signals:
            verdict = "Supportive with sensitivity"
        elif score >= 3:
            verdict = "Harmonious & Warm"
        elif score >= 1:
            verdict = "Moderate & Selective"
        else:
            verdict = "Guarded / Needs Care"
    elif akey == "health":
        if score >= 3:
            verdict = "Steady Vitality"
        elif score >= 1:
            verdict = "Balanced / Steady"
        else:
            verdict = "Needs Routine & Care"
    elif akey == "travel":
        if score >= 3:
            verdict = "Active Horizons"
        elif score >= 1:
            verdict = "Moderate / Occasional"
        else:
            verdict = "Quiet / Rooted"
    elif akey == "character":
        if supporting_signals and conflicting_signals:
            verdict = "Dynamic with competing pulls"
        elif score >= 3:
            verdict = "Strong & Purposeful"
        elif score >= 1:
            verdict = "Balanced & Adaptive"
        else:
            verdict = "Introspective / Guarded"
    else:
        if score >= 3:
            verdict = "Strong"
        elif score >= 1:
            verdict = "Moderate"
        else:
            verdict = "Needs Attention"

    if quality_grade == "poor":
        verdict = "Insufficient Evidence"

    # Practical "What helps"
    what_helps_map = {
        "career": "Concentrate on fewer priorities, take ownership of high-value work, and avoid unnecessary professional fragmentation.",
        "wealth": "Maintain disciplined accumulation, protect liquid cash flow, and avoid short-term emotional or speculative decisions.",
        "love": "Communicate feelings directly rather than relying on assumptions, and allow emotional trust to build at its natural pace.",
        "health": "Protect regular rest rhythms, maintain steady daily physical movement, and pause early when nervous fatigue appears.",
        "travel": "Channel restlessness into purposeful explorations, learning new disciplines, or refreshing changes of environment.",
        "character": "Anchor ambition with deliberate daily discipline, honor your personal standards, and let consistent actions demonstrate authority.",
    }
    what_helps = what_helps_map.get(akey, "Maintain steady focus, balance effort with rest, and act with intention.")

    # Timing breakdown
    current_phase = "Demanding but constructive — energy requires intentional focus." if conflicting_signals else "Favourable baseline — steady momentum."
    near_term = "Pressure remains while competing priorities are active; progress rewards patience." if conflicting_signals else "Continued steady development."

    return {
        "verdict": verdict,
        "confidence": confidence,
        "supporting_signals": supporting_signals,
        "conflicting_signals": conflicting_signals,
        "what_helps": what_helps,
        "current_phase": current_phase,
        "near_term": near_term,
    }


_MAX_POINTS_PER_ASPECT = 2
_ASTRO_LEAK = re.compile(
    r"\b(?:ascendant|capricorn|aquarius|pisces|aries|taurus|gemini|cancer|"
    r"leo|virgo|libra|scorpio|sagittarius|triplicity|weekday-born|paksha|"
    r"chart-from-palm|phalange)\b",
    re.I,
)


def _point_signature(text: str) -> frozenset[str]:
    """A light, deterministic near-duplicate check for customer copy."""
    words = re.findall(r"[a-z]{4,}", (text or "").lower())
    return frozenset(words)


def _is_distinct(text: str, accepted: list[dict[str, Any]]) -> bool:
    candidate = _point_signature(text)
    if not candidate:
        return False
    for point in accepted:
        prior = _point_signature(str(point.get("text") or ""))
        overlap = len(candidate & prior) / max(1, min(len(candidate), len(prior)))
        if overlap >= 0.72:
            return False
    return True


def _customer_safe_signal(signal: dict[str, Any]) -> bool:
    """Keep palm evidence, never the astro-palm bridge's speculative jargon."""
    text = str(signal.get("text") or "").strip()
    return bool(text) and not _ASTRO_LEAK.search(text)


def build_life_aspects(
    blocks: dict[str, Any],
    active_hand: str,
    *,
    saraswati_signals: Optional[dict[str, list[dict[str, Any]]]] = None,
) -> list[dict[str, Any]]:
    from pathlib import Path
    import json

    dom_key = "left" if active_hand == "left" else "right"
    non_key = "right" if dom_key == "left" else "left"
    dom = blocks.get(dom_key) or blocks.get("right") or blocks.get("left")
    if not dom:
        return []
    non = blocks.get(non_key)
    dom_quality = ((dom.get("features") or {}).get("quality") or {})
    quality_grade = str(dom_quality.get("grade") or "fair").lower()

    dv = View((dom.get("features") or {}))
    nv = View((non.get("features") or {})) if non else None

    rubric_path = Path(__file__).resolve().parent / "data" / "palm_modern_correlation.json"
    try:
        rubric = json.loads(rubric_path.read_text(encoding="utf-8")) if rubric_path.is_file() else {}
    except Exception:
        rubric = {}

    # Map aspect key to rule aspect categories
    aspect_rule_map: dict[str, tuple[str, ...]] = {
        "career": ("career", "fortune"),
        "wealth": ("wealth", "fortune"),
        "love": ("love",),
        "health": ("health",),
        "travel": ("travel",),
        "character": ("character", "mind", "fortune"),
    }

    out: list[dict[str, Any]] = []
    for akey, atitle in ASPECTS:
        allowed_rule_aspects = aspect_rule_map.get(akey, (akey,))
        matched: list[Rule] = []
        for r in RULES:
            if r.aspect not in allowed_rule_aspects or not _safe(r.cond, dv):
                continue
            if quality_grade != "good" and re.search(
                r"\b(trident|star|grille|triangle|square|cross)\b", r.text, re.I
            ):
                continue
            matched.append(r)
        if not matched:
            continue

        ranked = sorted(
            matched,
            key=lambda r: (
                1 if (nv and _safe(r.cond, nv)) else 0,
                len(r.text),
            ),
            reverse=True,
        )

        points: list[dict[str, Any]] = []
        seen_families: set[str] = set()
        for r in ranked:
            both = bool(nv and _safe(r.cond, nv))
            entry = rubric.get(r.rule_id) or rubric.get(akey, {}) or {}
            family = str(entry.get("family") or f"{akey}_general")

            if family in seen_families:
                continue

            text = str(entry.get("modern_meaning") or r.text).strip()
            if not text or not _is_distinct(text, points):
                continue

            recognize = list(entry.get("recognize") or [])
            if not recognize:
                recognize = _fallback_recognition(akey, r)

            points.append({
                "rule_id": r.rule_id,
                "family": family,
                "text": text,
                "recognize": recognize[:4],
                "reinforced": both,
                "book": r.book,
                "book_label": book_label(r.book) if r.book else None,
                "page": r.page,
                "quote": r.quote,
                "traditional_meaning": r.text,
                "claim_level": entry.get("claim_level", "pattern"),
            })
            seen_families.add(family)
            if len(points) >= _MAX_POINTS_PER_ASPECT:
                break

        if not points:
            continue

        reinforced = sum(1 for p in points if p.get("reinforced"))
        confluence_info = _calculate_confluence_verdict(akey, points, quality_grade, dv=dv, nv=nv)

        meaning_parts = [str(p["text"]).strip().rstrip(".") for p in points if p.get("text")]
        if len(meaning_parts) == 1:
            summary = meaning_parts[0] + "."
        else:
            summary = _combine_modern_meanings(akey, meaning_parts)

        recognition: list[str] = []
        for p in points:
            for item in p.get("recognize") or []:
                if item not in recognition:
                    recognition.append(item)
                if len(recognition) >= 4:
                    break
            if len(recognition) >= 4:
                break

        upaya_info = _ASPECT_VEDIC_UPAYAS.get(akey) or {}
        remedy_text = upaya_info.get("upaya", "")

        out.append({
            "key": akey,
            "title": atitle,
            "summary": summary,
            "what_it_means": summary,
            "recognition_title": "You may recognize this as",
            "recognize": recognition,
            "strength": confluence_info["verdict"],
            "strength_note": confluence_info["current_phase"],
            "confidence": confluence_info["confidence"],
            "verdict": confluence_info["verdict"],
            "supporting_signals": confluence_info["supporting_signals"],
            "conflicting_signals": confluence_info["conflicting_signals"],
            "what_helps": confluence_info["what_helps"],
            "current_phase": confluence_info["current_phase"],
            "near_term": confluence_info["near_term"],
            "reinforced_count": reinforced,
            "points": points,
            "remedy": remedy_text,
            "planet": upaya_info.get("planet", ""),
        })

    # Saraswati book lane — keep it as evidence, but do not allow it to create
    # a new customer-facing life theme by itself.
    extra = saraswati_signals or {}
    by_key = {row["key"]: row for row in out}
    for akey, sigs in extra.items():
        if akey not in dict(ASPECTS):
            continue
        row = by_key.get(akey)
        if not row:
            continue
        for sig in sigs:
            if len(row["points"]) >= _MAX_POINTS_PER_ASPECT:
                break
            txt = (sig.get("text") or "").strip()
            if not _customer_safe_signal(sig):
                continue
            # The bridge signal is evidence, not a new modern-life claim.
            if not _is_distinct(txt, row["points"]):
                continue
            row["points"].append({
                "rule_id": "saraswati",
                "family": "supporting_evidence",
                "text": row["summary"],
                "recognize": [],
                "reinforced": bool(sig.get("reinforced")),
                "book": None,
                "book_label": None,
                "page": None,
                "quote": "",
                "traditional_meaning": txt,
                "claim_level": "supporting",
            })

    return out


def _fallback_recognition(aspect: str, rule: Rule) -> list[str]:
    """Safe generic recognition cues when a new rule lacks a rubric entry."""
    defaults = {
        "character": [
            "the way you respond to people or pressure",
            "how comfortable you feel taking the lead or holding back",
        ],
        "mind": [
            "how you make important decisions",
            "whether you prefer facts, discussion or intuition before acting",
        ],
        "love": [
            "how quickly you open up to someone",
            "what you need to feel secure in a close relationship",
        ],
        "career": [
            "the kind of responsibility you naturally take on",
            "how recognition or independence affects your work choices",
        ],
        "wealth": [
            "how you approach earning, saving or financial risk",
            "whether skill, reputation or planning matters to your income",
        ],
        "health": [
            "how strongly routine, rest and recovery affect your day",
            "whether stress changes how energetic you feel",
        ],
        "travel": [
            "whether you feel refreshed by change of place",
            "how much variety you need to stay mentally engaged",
        ],
        "fortune": [
            "a period when one area of life feels unusually supported",
            "opportunities that seem to arrive when you are ready to use them",
        ],
    }
    return defaults.get(aspect, [])


def _combine_modern_meanings(aspect: str, meanings: list[str]) -> str:
    """Combine two independent modern manifestations without sounding like a list."""
    a, b = meanings[0], meanings[1]
    # The entries in the rubric are already complete human sentences.
    # Joining them as sentences is clearer than trying to grammatically splice
    # two full sentences with words such as "combines" or "alongside".
    lead = {
        "character": "Together, these signs point to two related parts of your temperament:",
        "mind": "Together, these signs point to two related parts of how you think and decide:",
        "love": "Together, these signs point to two related parts of your emotional life:",
        "career": "Together, these signs point to two related parts of your work life:",
        "wealth": "Together, these signs point to two related parts of how you build security:",
        "health": "Together, these signs point to two related wellbeing patterns:",
        "travel": "Together, these signs point to two related ways you respond to change:",
        "fortune": "Together, these signs point to two related supportive themes:",
    }.get(aspect, "Together, these signs point to two related patterns:")
    return f"{lead} {a}. {b}."


def _safe(cond: Callable[[View], bool], v: View) -> bool:
    try:
        return bool(cond(v))
    except Exception:
        return False
