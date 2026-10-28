"""Palmist voice — the reading a palmist gives out loud, from measured features.

`palm_voice.py` writes the short prediction chips used by the cards report. This
module does the other half of the job: it takes the raw feature dict produced by
`analyzer.extract_features` and turns each measurement into the three things a
palmist actually says while holding a hand —

    the sign      "your head line stays joined to the life line for a long start"
    the reading   what the books make of that sign
    the answer    what to do about it, when the sign is a difficult one

Every entry is keyed to a measurement the CV produced. Nothing here fires on a
feature that was not detected, so the report can never claim a mark that is not
in the photograph.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

# ---------------------------------------------------------------------------
# vocabulary
# ---------------------------------------------------------------------------
# Palmists name the mounts after the planets and readers expect that language.
# The plain-English gloss rides alongside so nobody has to already know it.
MOUNT_NAME = {
    "jupiter": "Mount of Jupiter",
    "saturn": "Mount of Saturn",
    "apollo": "Mount of Apollo",
    "sun": "Mount of Apollo",
    "mercury": "Mount of Mercury",
    "mars": "Mount of Mars",
    "venus": "Mount of Venus",
    "moon": "Mount of Luna",
    "luna": "Mount of Luna",
}

MOUNT_WHERE = {
    "jupiter": "the pad under your index finger",
    "saturn": "the pad under your middle finger",
    "apollo": "the pad under your ring finger",
    "sun": "the pad under your ring finger",
    "mercury": "the pad under your little finger",
    "mars": "the pads either side of your palm at thumb height",
    "venus": "the ball of your thumb",
    "moon": "the soft outer edge below your little finger",
    "luna": "the soft outer edge below your little finger",
}

MOUNT_RULES = {
    "jupiter": "ambition, confidence and how naturally you take charge",
    "saturn": "patience, discipline and how you carry duty",
    "apollo": "creativity, taste and public recognition",
    "sun": "creativity, taste and public recognition",
    "mercury": "speech, trade, persuasion and quick wit",
    "mars": "courage, stamina and temper",
    "venus": "warmth, appetite for life and physical vitality",
    "moon": "imagination, moods, travel and intuition",
    "luna": "imagination, moods, travel and intuition",
}

LINE_NAME = {
    "life": "Life line",
    "head": "Head line",
    "heart": "Heart line",
    "fate": "Fate line",
    "sun": "Sun line",
    "mercury": "Health line",
    "marriage": "Marriage lines",
    "girdle_of_venus": "Girdle of Venus",
    "ring_of_solomon": "Ring of Solomon",
    "children": "Children lines",
    "travel": "Travel lines",
}

LINE_WHERE = {
    "life": "the curve wrapping the ball of your thumb",
    "head": "the line running across the middle of your palm",
    "heart": "the upper line running below your fingers",
    "fate": "the line rising up the centre of your palm",
    "sun": "the short line rising towards your ring finger",
    "mercury": "the line rising towards your little finger",
    "marriage": "the small lines on the edge below your little finger",
    "girdle_of_venus": "the arc above your heart line",
    "ring_of_solomon": "the small arc around the base of your index finger",
    "children": "the fine uprights above the marriage lines",
    "travel": "the short lines on the outer edge of your palm",
}


@dataclass(frozen=True)
class Reading:
    """One thing the palmist saw, what it means, and what to do about it."""

    key: str
    feature: str
    sign: str
    means: str
    tone: str = "neutral"  # "strong" | "care" | "neutral"
    remedy: str = ""
    hand: str = ""
    age: Optional[int] = None
    age_range: tuple[int, int] | None = None
    where: str = ""

    @property
    def is_problem(self) -> bool:
        return self.tone == "care"


@dataclass
class HandReading:
    hand: str
    grade: str = "fair"
    marks_allowed: bool = False
    shape: list[Reading] = field(default_factory=list)
    lines: list[Reading] = field(default_factory=list)
    minor: list[Reading] = field(default_factory=list)
    mounts: list[Reading] = field(default_factory=list)
    marks: list[Reading] = field(default_factory=list)

    def all(self) -> list[Reading]:
        return self.shape + self.lines + self.minor + self.mounts + self.marks

    def problems(self) -> list[Reading]:
        return [r for r in self.all() if r.is_problem]


def _val(block: Any, key: str) -> str:
    if not isinstance(block, dict):
        return ""
    return str(block.get(key) or "").strip().lower()


def _mk(key: str, feature: str, sign: str, means: str, *, tone: str = "neutral",
        remedy: str = "", hand: str = "", where: str = "") -> Reading:
    return Reading(key=key, feature=feature, sign=sign, means=means, tone=tone,
                   remedy=remedy, hand=hand, where=where)


# ---------------------------------------------------------------------------
# hand shape, thumb and fingers
# ---------------------------------------------------------------------------
_HAND_TYPE = {
    "air": ("a square palm with long, slender fingers — an Air hand",
            "You are an intuitive thinker, strategist, and communicator. You thrive on mental variety, "
            "meaningful conversation, and intellectual challenge. Monotony or rigid repetitive work drains you "
            "faster than hard mental labor, and you need a clear reason before you commit your energy.",
            "neutral", ""),
    "earth": ("a square palm with sturdy, grounded fingers — an Earth hand",
              "You are practical, dependable, and deeply grounded. You trust what is tangible, measurable, and reliable. "
              "Where fast-paced chaos exhausts others, routine steadies you, and when you give your word, you see it through.",
              "neutral", ""),
    "fire": ("a long palm with quick, energetic fingers — a Fire hand",
             "You are dynamic, instinctive, and driven by passion. You act with enthusiasm and inspire momentum. "
             "Your challenge is rarely starting — it is sustaining focus on one project until it reaches full completion.",
             "neutral", "Focus your energy on completing one primary goal before opening a new front. "
             "A Fire hand creates immense value through disciplined finishing."),
    "water": ("a long, elegant palm with sensitive fingers — a Water hand",
              "You possess deep emotional intelligence and absorb the atmosphere around you instantly. "
              "Your intuition often knows the truth before logic catches up, making empathy your greatest strength.",
              "neutral", ""),
}

_THUMB_WILL = {
    "will_dominant": ("a thumb with a strong, determined upper phalanx",
                      "Your willpower naturally leads the way. Once your mind is made up, you push forward with unwavering conviction. "
                      "This determination creates breakthrough results, provided you pause to verify the course.",
                      "neutral",
                      "Before major life commitments, intentionally seek out one counter-perspective. "
                      "A strong-willed thumb benefits greatly from deliberate second checks."),
    "logic_dominant": ("a thumb with a longer lower phalanx of reasoning",
                       "Your analytical mind sees solutions and risks well ahead of others. You map out every step with clarity, "
                       "though you occasionally spend too long analyzing before making the final move.",
                       "care",
                       "Set a firm deadline for the decision itself rather than the execution. "
                       "Trust your analysis and take action once the core facts are clear."),
    "balanced": ("a thumb with beautifully balanced will and logic sections",
                 "You possess what classical palmistry calls the 'Governing Thumb' — a harmonious balance where thoughtful planning "
                 "and decisive action move in seamless alignment.", "strong", ""),
}


def read_shape(feats: dict, *, hand: str = "") -> list[Reading]:
    morph = feats.get("morphology") or {}
    out: list[Reading] = []

    htype = _val(morph, "hand_type")
    if htype in _HAND_TYPE:
        sign, means, tone, remedy = _HAND_TYPE[htype]
        out.append(_mk(f"hand_type_{htype}", "Your hand shape", sign, means,
                       tone=tone, remedy=remedy, hand=hand))

    thumb = morph.get("thumb") or {}
    will = _val(thumb, "will_vs_logic")
    if will in _THUMB_WILL:
        sign, means, tone, remedy = _THUMB_WILL[will]
        out.append(_mk(f"thumb_{will}", "Your thumb", sign, means, tone=tone,
                       remedy=remedy, hand=hand, where="the thumb"))

    length = _val(thumb, "length")
    if length == "long":
        out.append(_mk("thumb_long", "Thumb length", "a long, commanding thumb",
                       "Leadership and managerial responsibility come naturally to you. People look to you for direction, "
                       "and you often find yourself steering initiatives you only joined to support.", tone="strong", hand=hand))
    elif length == "short":
        out.append(_mk(
            "thumb_short", "Thumb length", "a receptive thumb",
            "You lead with heart, empathy, and adaptability. You are generous in discussions, though you must guard against "
            "giving away leverage too easily in negotiations.",
            tone="care", hand=hand,
            remedy="Establish your core non-negotiables before entering important discussions, and state your boundary clearly up front."))

    opening = _val(thumb, "opening")
    if opening == "wide":
        out.append(_mk("thumb_open", "Thumb angle", "a wide, open-set thumb",
                       "Generous, independent, and open-minded. You readily share your knowledge, resources, and hospitality, "
                       "holding a natural sense of abundance.",
                       tone="neutral", hand=hand))
    elif opening in ("narrow", "close"):
        out.append(_mk(
            "thumb_closed", "Thumb angle", "a close-set, protective thumb",
            "Prudent and discreet. You protect your resources, plans, and inner feelings with wise caution, "
            "avoiding unnecessary risks.",
            tone="neutral", hand=hand))

    idx = _val(morph, "index_vs_ring")
    if idx == "index_longer":
        out.append(_mk("index_long", "Your index finger",
                       "an index finger longer than your ring finger",
                       "You have a natural drive for autonomy, leadership, and personal standard-setting. "
                       "You thrive when you have full ownership of your domain.", tone="neutral",
                       hand=hand))
    elif idx == "ring_longer":
        out.append(_mk("ring_long", "Your ring finger",
                       "a ring finger longer than your index finger",
                       "You possess creative flair, calculated risk appetite, and strong personal charisma. "
                       "Meaningful recognition and creative impact inspire you deeply.", tone="neutral",
                       hand=hand))
    return out


# ---------------------------------------------------------------------------
# the four major lines
# ---------------------------------------------------------------------------
_LIFE = {
    "depth": {
        "deep": ("runs deep, smooth and clearly etched",
                 "You possess robust vitality and natural resilience. You bounce back from physical fatigue, stress, and intense working "
                 "stretches faster than most people around you, possessing a strong constitutional reserve.", "strong", ""),
        "medium": ("runs at an even, healthy depth",
                   "You have steady, sustainable vitality. You manage energy best with consistent rhythms, balanced pacing, "
                   "and avoiding sudden extreme over-exertion.", "neutral", ""),
        "shallow": ("runs fine and lightly drawn",
                    "Your energy operates through nervous and mental drive rather than raw physical reserve. You give deeply to your work, "
                    "which makes intentional restorative rest essential.", "care",
                    "Prioritize restorative sleep and physical recovery. On this line, pacing yourself is the key to sustained success."),
    },
    "sweep": {
        "wide": ("sweeps broadly around the base of your thumb",
                 "You have a wide appetite for living — you crave meaningful human connection, travel, vibrant experiences, "
                 "and dynamic environments. You do not just want to work; you want to truly experience life.",
                 "strong", ""),
        "narrow": ("curves closely around the thumb",
                   "Your energy is focused inward. A close inner circle, peaceful home surroundings, and quiet focus restore you best, "
                   "whereas large noisy crowds drain you.", "neutral", ""),
    },
    "quality": {
        "broken": ("shows an overlapping shift",
                   "A clean shift in your life line signifies a major life upgrade or relocation — a change of environment, career direction, "
                   "or lifestyle where you reinvented your personal foundation on your own terms.",
                   "care",
                   "During transition years, focus on building sustainable daily routines before taking on rigid long-term obligations."),
        "chained": ("shows a textured or chained stretch",
                     "A chained stretch reflects temporary energy drains or scattered commitments that divide your focus.", "care",
                     "Identify one recurring distraction and remove it. A focused line brings immediate clarity and vitality."),
        "islanded": ("carries an enclosed protective loop",
                     "A temporary split in energy where health, family care, or external duties demanded a share of your attention.", "care",
                     "Lighten non-essential commitments during demanding periods and prioritize your well-being."),
    },
}

_HEAD = {
    "depth": {
        "deep": ("is deeply and sharply cut",
                 "You possess profound concentration, analytical depth, and strategic thinking. You have the ability to hold complex problems "
                 "in your mind until you discover the optimal breakthrough, thinking things through before you speak.", "strong", ""),
        "shallow": ("is lightly etched",
                    "Your thoughts move rapidly and intuitively. You generate brilliant initial concepts, though delegating or structuring "
                    "the operational follow-through helps you succeed.", "care",
                    "Capture your ideas in writing immediately. A creative mind flourishes when ideas are anchored onto paper."),
    },
    "length": {
        "long": ("runs long and steady across the palm",
                 "You are a long-range strategist. You naturally see the second- and third-order consequences of any decision, "
                 "which makes your judgment exceptionally reliable and calculated.", "strong", ""),
        "short": ("is concise and direct",
                  "You are pragmatic, decisive, and action-oriented. You prefer quick, direct solutions over endless theoretical deliberation.", "neutral",
                  ""),
    },
    "direction": {
        "moon": ("slopes gently toward the creative lower palm",
                 "Logic and creative imagination blend seamlessly in your thinking. You solve problems through lateral intuition, "
                 "and you thrive when your work allows creative autonomy.", "neutral",
                 "Maintain a creative hobby or personal project outside your routine work to keep your mind energized."),
        "straight": ("extends straight across the palm",
                     "You have a practical, realistic, and objective mind. You respect verifiable facts, clear milestones, "
                     "and straightforward communication.", "neutral", ""),
        "upward": ("curves upward toward the little finger",
                   "You have strong commercial acumen, financial sense, and negotiation instincts. You spot market openings and practical value quickly.",
                   "strong", ""),
    },
    "start_relation": {
        "merged": ("stays joined with the life line at its origin",
                   "You developed early caution and deep respect for family guidance. While this thoughtful prudence protected you from reckless risks, "
                   "your hand shows that you achieve your greatest successes when you step forward and trust your own independent authority.", "care",
                   "Make key decisions with quiet confidence without seeking unanimous approval from others first."),
        "separate": ("begins independently from the life line",
                     "You are naturally independent and self-directed. You trusted your own judgment early in life and thrive with autonomy.", "strong", ""),
        "wide": ("starts with a distinct gap from the life line",
                 "You are bold, spontaneous, and quick to seize opportunities. You move with speed, trusting your instincts to adapt as you go.",
                 "neutral",
                 "Sleep on high-stakes, irreversible decisions for one night to let your natural logic refine the plan."),
    },
    "quality": {
        "broken": ("shows a transition point",
                   "A major shift in perspective or intellectual career focus where you outgrew an old paradigm and stepped into a new domain.", "care",
                   "Give yourself room to explore when entering new intellectual chapters."),
        "islanded": ("carries an island formation",
                     "A period of mental overwork or competing priorities that divided your attention.", "care",
                     "Simplify your focus by handling one core priority at a time."),
        "chained": ("shows a chained texture",
                     "A stretch of mental fatigue or multitasking overload.", "care",
                     "Schedule dedicated distraction-free focus blocks during your work day."),
    },
}

_HEART = {
    "depth": {
        "deep": ("is deeply etched",
                 "You are sincere, loyal, and deeply invested in the relationships that matter to you. When you commit, you do so wholeheartedly "
                 "and value genuine emotional authenticity in return.", "strong", ""),
        "shallow": ("is lightly marked",
                    "You feel deeply but express emotions subtly and privately. Others may perceive you as composed or reserved.", "care",
                    "Express appreciation openly in words to close ones. Clear expression deepens trust rapidly."),
    },
    "start_zone": {
        "jupiter": ("reaches high toward the index finger",
                    "The noble idealist in love and friendship. You hold high ethical standards and loyalty, seeking partners of character.", "neutral", ""),
        "saturn": ("originates under the middle finger",
                   "You express dedication through dependable actions, practical support, and steady loyalty rather than grand dramatic gestures.", "neutral",
                   "Complement your practical support with verbal appreciation to nurture closer emotional bonds."),
        "between": ("begins gracefully between the index and middle fingers",
                    "The ideal emotional equilibrium — you offer warmth, fair expectations, healthy boundaries, and resilient balance.",
                    "strong", ""),
    },
    "length": {
        "short": ("is focused and concise",
                  "You maintain a close, carefully chosen circle of trusted confidants rather than spreading emotional energy thin.", "neutral", ""),
        "long": ("extends across the palm",
                 "You possess deep empathy, enduring loyalty, and strong commitment to the people you care about.",
                 "neutral", ""),
    },
    "quality": {
        "broken": ("shows an emotional transition",
                   "A significant period of emotional growth or boundary-setting that clarified what truly matters to your heart.", "care",
                   "Communicate your inner values early and clearly in close relationships."),
        "chained": ("shows sensitive chaining",
                     "A period of emotional sensitivity or navigating complex relationship dynamics.", "care",
                     "Ground yourself in clear personal boundaries and open conversations."),
        "islanded": ("carries an island formation",
                     "A temporary stretch of emotional deliberation or divided loyalty.", "care",
                     "Give yourself time before making permanent relationship commitments."),
    },
}

_FATE = {
    "depth": {
        "deep": ("runs strong, steady and clear",
                 "You have strong sense of purpose and career alignment. Your dedicated effort compounds into real standing and lasting achievements.",
                 "strong", ""),
        "shallow": ("runs lightly drawn",
                    "Your path is self-forged through adaptable exploration. Your greatest career clarity develops as you gain experience.", "neutral", ""),
    },
    "start_zone": {
        "wrist": ("rises cleanly from the base of the palm",
                  "You discovered your natural calling and career ambition early, building a steady trajectory.", "strong", ""),
        "mid_palm": ("emerges with strength in the mid-palm",
                     "Your true career breakthrough and personal authority blossom in mid-career (ages 30–45), where you transition into the work that genuinely fits you.", "neutral", ""),
        "moon": ("originates from the creative outer palm",
                 "Your success is amplified through collaboration, public engagement, specialized clients, and interpersonal trust.", "strong", ""),
        "venus": ("rises from the ball of the thumb",
                  "Family and early support are woven into your career. Help "
                  "came from close to home — and so, sometimes, did the "
                  "obligation.", "neutral", ""),
    },
    "quality": {
        "broken": ("is broken",
                   "A broken fate line means the work changes shape mid-course. "
                   "Classically this is a change of role, employer or field, not "
                   "a loss of livelihood.", "care",
                   "Keep six months of running costs to hand across that stretch, "
                   "and keep your skills portable."),
        "wavy": ("runs wavy rather than straight",
                 "A wavy fate line is read as a career that moves in stages — "
                 "several turns rather than one climb.", "care",
                 "Stop treating each turn as a false start. On this line the "
                 "range you build across the moves is the actual asset."),
        "islanded": ("carries an island",
                     "An island on the fate line marks a stretch of stalled or "
                     "divided work.", "care",
                     "Use that window to qualify or retrain rather than to push "
                     "for promotion."),
    },
}

_MAJOR = {"life": _LIFE, "head": _HEAD, "heart": _HEART, "fate": _FATE}

# Attributes are read in the order a palmist would call them out.
_ORDER = {
    "life": ("depth", "sweep", "quality"),
    "head": ("start_relation", "depth", "length", "direction", "quality"),
    "heart": ("depth", "start_zone", "length", "quality"),
    "fate": ("depth", "start_zone", "quality"),
}


def _line_missing(key: str) -> Optional[Reading]:
    if key == "fate":
        return _mk(
            "fate_absent", LINE_NAME["fate"], "no clear fate line in this hand",
            "The books do not read an absent fate line as failure — they read it "
            "as a life not run on rails. Nothing external is going to hand you a "
            "direction, and nothing external is going to take one away either.",
            tone="neutral",
            remedy="Choose the structure yourself: fixed hours, a stated goal, a "
                   "person you report to. Hands without this line do better with "
                   "a frame they built than with one they waited for.",
            where=LINE_WHERE["fate"])
    return None


# Two entries that reach the same verdict make the reading sound like padding.
# Where a pair overlaps, the second is dropped in favour of the more specific.
_REDUNDANT = {
    "head_length_short": "head_direction_straight",
    "head_length_long": "head_direction_moon",
}

#: A palmist calls out the two or three things that decide the line, not every
#: attribute that was measurable.
_MAX_PER_LINE = 3


def read_lines(feats: dict, *, hand: str = "") -> list[Reading]:
    lines = feats.get("lines") or {}
    out: list[Reading] = []
    for key in ("life", "head", "heart", "fate"):
        block = lines.get(key) or {}
        if not block.get("detected"):
            missing = _line_missing(key)
            if missing:
                out.append(Reading(**{**missing.__dict__, "hand": hand}))
            continue
        table = _MAJOR[key]
        found: list[Reading] = []
        for attr in _ORDER[key]:
            value = _val(block, attr)
            # `quality` reports "clear" for a sound line; there is nothing for a
            # palmist to say about that beyond what depth already said.
            if attr == "quality" and value in ("", "clear"):
                # A wavy shape is a quality statement on the fate line only.
                if key == "fate" and _val(block, "shape") == "wavy":
                    value = "wavy"
                else:
                    continue
            entry = table.get(attr, {}).get(value)
            if not entry:
                continue
            sign, means, tone, remedy = entry
            found.append(_mk(f"{key}_{attr}_{value}", LINE_NAME[key], sign, means,
                             tone=tone, remedy=remedy, hand=hand,
                             where=LINE_WHERE[key]))
        present = {r.key for r in found}
        found = [r for r in found if _REDUNDANT.get(r.key) not in present]
        # Warnings and strengths outrank the merely descriptive when the line
        # produced more observations than a reading would state out loud.
        if len(found) > _MAX_PER_LINE:
            rank = {"care": 0, "strong": 1, "neutral": 2}
            order = {r.key: i for i, r in enumerate(found)}
            found = sorted(found, key=lambda r: (rank.get(r.tone, 2), order[r.key]))
            found = sorted(found[:_MAX_PER_LINE], key=lambda r: order[r.key])
        out.extend(found)
    return out


# ---------------------------------------------------------------------------
# minor lines
# ---------------------------------------------------------------------------
_MINOR_PRESENT = {
    "sun": ("You carry a Sun line",
            "The line of recognition. Work you do well gets seen — you are not "
            "one of the people who has to shout to be noticed.", "strong", ""),
    "mercury": ("You carry a Health line",
                "A Mercury line is read as a nervous, quick constitution tied to "
                "the stomach and the mind together. When the mind is overloaded, "
                "digestion is where you feel it first.", "care",
                "Eat at fixed hours in your heavy weeks. On this line the stomach "
                "reports the stress before you admit to it."),
    "marriage": ("You carry marriage lines",
                 "The lines of significant attachment — the partnerships deep "
                 "enough to change how you live, not every relationship you have "
                 "had.", "neutral", ""),
    "girdle_of_venus": ("You carry a Girdle of Venus",
                        "A sensitive, highly-strung emotional register. You feel "
                        "everything at full volume, which makes you good with "
                        "people and expensive to be.", "care",
                        "Take the mood seriously but not literally. On this arc "
                        "the feeling is real and the conclusion it reaches at "
                        "midnight usually is not."),
    "ring_of_solomon": ("You carry a Ring of Solomon",
                        "The teacher's mark. You understand people quickly and "
                        "they bring you their problems whether or not you asked "
                        "for them.", "strong", ""),
    "travel": ("You carry travel lines",
               "Movement is written into the hand — journeys, relocations, or a "
               "restlessness that has to be spent somewhere.", "neutral", ""),
    "children": ("You carry children lines",
                 "The fine uprights the books tie to children or to those you "
                 "raise as your own.", "neutral", ""),
}

_MINOR_ABSENT = {
    "sun": ("No clear Sun line",
            "Recognition will come from being asked for by name, not from being "
            "noticed in a crowd. Build the reputation with a few people who can "
            "vouch for you.", "neutral",
            "Ask for the referral or the testimonial. Hands without this line "
            "have to be introduced rather than discovered."),
    "girdle_of_venus": ("No Girdle of Venus",
                        "You are not carried away by feeling. Emotion does not "
                        "run the decision, which is steadying for you and "
                        "occasionally cold for the people close to you.",
                        "neutral", ""),
}


def read_minor(feats: dict, *, hand: str = "") -> list[Reading]:
    minor = feats.get("minor_lines") or {}
    out: list[Reading] = []
    for key, block in minor.items():
        name = LINE_NAME.get(key) or str((block or {}).get("title") or key)
        where = LINE_WHERE.get(key, "")
        if (block or {}).get("detected"):
            entry = _MINOR_PRESENT.get(key)
            if not entry:
                continue
            sign, means, tone, remedy = entry
            strength = _val(block, "strength")
            if strength == "faint":
                sign += ", faintly marked"
            elif strength == "strong":
                sign += ", strongly marked"
            out.append(_mk(f"minor_{key}", name, sign, means, tone=tone,
                           remedy=remedy, hand=hand, where=where))
        else:
            entry = _MINOR_ABSENT.get(key)
            if not entry:
                continue
            sign, means, tone, remedy = entry
            out.append(_mk(f"minor_no_{key}", name, sign, means, tone=tone,
                           remedy=remedy, hand=hand, where=where))
    return out


# ---------------------------------------------------------------------------
# mounts
# ---------------------------------------------------------------------------
_MOUNT_LEVEL = {
    "prominent": {
        "jupiter": ("You lead without being asked to, and you feel wrong in a "
                    "room where somebody else is deciding badly.", "strong",
                    "Say what you want out loud. A full Jupiter mount that stays "
                    "quiet turns into resentment."),
        "saturn": ("Patience and duty are heavy in this hand. You will carry a "
                   "long, unglamorous job further than most people could — and "
                   "you will carry it alone if nobody stops you.", "care",
                   "Hand one duty to somebody else this month. A full Saturn "
                   "mount does not delegate until it is told to."),
        "apollo": ("Taste, style and creative confidence. You care how a thing "
                   "looks and you are usually right about it.", "strong", ""),
        "mercury": ("Speech and trade. You can explain, sell and negotiate, and "
                    "you talk your way into rooms other people queue for.",
                    "strong", ""),
        "mars": ("High courage and a hot temper on the same pad. You do not back "
                 "down, which is a gift in a crisis and a bill everywhere else.",
                 "care",
                 "Wait one full day before answering anything that angered you. "
                 "On a full Mars mount the temper is faster than the judgement."),
        "venus": ("Warmth, appetite and physical vitality. You need affection, "
                  "good food and company the way other hands need rest.",
                  "strong", ""),
        "moon": ("A strong imagination — and a mind that will write you a full "
                 "story out of very little evidence at two in the morning.",
                 "care",
                 "Test the story against one fact before you act on it. A full "
                 "Luna mount predicts more than it observes."),
    },
    "flat": {
        "jupiter": ("Ambition is quiet here. You will do excellent work and let "
                    "somebody else describe it upward.", "care",
                    "Put your own name on your results once this quarter. A flat "
                    "Jupiter mount is passed over, not disliked."),
        "saturn": ("Little patience for duty for its own sake. Long, joyless "
                   "obligations will not hold you, so do not take them on.",
                   "neutral", ""),
        "apollo": ("Recognition is not what drives you, and public work will "
                   "feel like a costume.", "neutral", ""),
        "mercury": ("Speaking up is the effort here, not the thinking. You know "
                    "more than you say in the room.", "care",
                    "Prepare the one sentence you want heard before the meeting "
                    "starts. A flat Mercury mount loses credit to silence."),
        "mars": ("Confrontation costs you. You will let a thing run rather than "
                 "have the argument about it.", "care",
                 "Raise the small objection early, while it is still small. This "
                 "mount does not get louder later, it just gets tired."),
        "venus": ("Physical warmth is rationed. You are affectionate in private "
                  "and reserved everywhere else, and you tire before you expect "
                  "to.", "care",
                  "Guard your rest deliberately. A flat Venus mount runs out of "
                  "reserve without giving you much warning."),
        "moon": ("Feet firmly on the ground. Imagination does not run away with "
                 "you, and fantasy holds no interest.", "neutral", ""),
    },
}


def read_mounts(feats: dict, *, hand: str = "") -> list[Reading]:
    mounts = feats.get("mounts") or {}
    out: list[Reading] = []
    for key, level in mounts.items():
        level = str(level or "").lower()
        entry = _MOUNT_LEVEL.get(level, {}).get(str(key).lower())
        if not entry:
            continue
        means, tone, remedy = entry
        name = MOUNT_NAME.get(str(key).lower(), f"{str(key).title()} mount")
        where = MOUNT_WHERE.get(str(key).lower(), "your palm")
        rules = MOUNT_RULES.get(str(key).lower(), "this part of life")
        sign = (f"{'full and raised' if level == 'prominent' else 'flat'} at "
                f"{where}, the pad that rules {rules}")
        out.append(_mk(f"mount_{key}_{level}", name, sign, means, tone=tone,
                       remedy=remedy, hand=hand, where=where))
    return out


# ---------------------------------------------------------------------------
# special marks
# ---------------------------------------------------------------------------
_MARK_TONE = {
    "cross": "care", "grille": "care", "island": "care", "break": "care",
    "star": "neutral", "triangle": "strong", "square": "strong",
    "trident": "strong", "trishul": "strong", "fish": "strong",
}

_MARK_REMEDY = {
    "grille": "Do not push this area harder while the grille is on it. The books "
              "read a grille as effort scattering rather than failing.",
    "island": "Treat this as a stretch to protect rather than to expand. Keep "
              "commitments in it short and reversible.",
    "cross": "Take the warning literally and the timing loosely: be careful in "
             "this part of life, without arranging your years around a date.",
}


def read_marks(feats: dict, *, hand: str = "", allowed: bool = False) -> list[Reading]:
    """Named marks, in book language. Silent unless this hand's photo allows it."""
    if not allowed:
        return []
    out: list[Reading] = []
    for mark in feats.get("special_marks") or []:
        if not isinstance(mark, dict):
            continue
        kind = str(mark.get("type") or mark.get("kind") or "").lower()
        zone = str(mark.get("zone") or mark.get("mount") or "").lower()
        title = str(mark.get("title") or kind.title() or "Mark").strip()
        meaning = str(mark.get("meaning") or "").strip()
        if not meaning:
            continue
        place = MOUNT_NAME.get(zone)
        where = MOUNT_WHERE.get(zone, "your palm")
        sign = (f"a {kind or 'mark'} on your {place}" if place
                else f"a {kind or 'mark'} on your palm")
        tone = _MARK_TONE.get(kind, "neutral")
        remedy = _MARK_REMEDY.get(kind, "")
        if kind == "cross" and zone == "jupiter":
            # The books read a cross on Jupiter as a good sign (a union), so it is
            # neither flagged "needs care" nor given the warning remedy.
            tone, remedy = "neutral", ""
        out.append(_mk(f"mark_{kind}_{zone}", title, sign, meaning, tone=tone,
                       remedy=remedy, hand=hand, where=where))
    return out


# ---------------------------------------------------------------------------
# per-hand assembly
# ---------------------------------------------------------------------------
def hand_marks_allowed(hand_block: dict) -> bool:
    """Fine marks are a property of *this* photograph, not of the pair.

    A clear left hand and a blurred right hand are common. Gating both on the
    worse photo throws away a mark the camera genuinely resolved, so each hand
    answers for its own image.
    """
    quality = (hand_block.get("features") or {}).get("quality") or {}
    if "special_marks_allowed" in quality:
        return bool(quality.get("special_marks_allowed"))
    return str(quality.get("grade") or "").lower() == "good"


def read_hand(hand_block: dict, *, hand: str = "") -> HandReading:
    feats = (hand_block or {}).get("features") or {}
    quality = feats.get("quality") or {}
    allowed = hand_marks_allowed(hand_block or {})
    return HandReading(
        hand=hand,
        grade=str(quality.get("grade") or "fair").lower(),
        marks_allowed=allowed,
        shape=read_shape(feats, hand=hand),
        lines=read_lines(feats, hand=hand),
        minor=read_minor(feats, hand=hand),
        mounts=read_mounts(feats, hand=hand),
        marks=read_marks(feats, hand=hand, allowed=allowed),
    )


def dated_events(hand_block: dict, *, hand: str = "") -> list[Reading]:
    """Line findings that the timing engine could place at an age."""
    out: list[Reading] = []
    for item in (hand_block or {}).get("numbered_checklist") or []:
        if not isinstance(item, dict) or item.get("kind") != "line":
            continue
        timing = item.get("timing") or {}
        age = timing.get("estimated_age")
        if not isinstance(age, int):
            continue
        rng = timing.get("age_range") or []
        span = (int(rng[0]), int(rng[1])) if len(rng) == 2 else None
        key = str(item.get("key") or "")
        conc = item.get("conclusive") or {}
        means = str(conc.get("conclusion") or item.get("finding") or "").strip()
        out.append(Reading(
            key=f"dated_{key}_{age}",
            feature=LINE_NAME.get(key, str(item.get("title") or "Line")),
            sign=f"the marking at this point on your {LINE_NAME.get(key, 'line').lower()}",
            means=means, tone="neutral", hand=hand, age=age, age_range=span,
            where=LINE_WHERE.get(key, "")))
    return sorted(out, key=lambda r: r.age or 0)


def problems(readings: Iterable[Reading]) -> list[Reading]:
    return [r for r in readings if r.is_problem]
