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
    "air": ("a square palm with long fingers — an air hand",
            "You are a thinker and a talker before you are a doer. The books give "
            "this hand to people who need conversation, variety and a reason "
            "before they will commit to anything.",
            "neutral", ""),
    "earth": ("a square palm with short, firm fingers — an earth hand",
              "You trust what you can handle and finish. Routine steadies you "
              "where it would flatten a lighter hand, and you keep your word.",
              "neutral", ""),
    "fire": ("a long palm with short fingers — a fire hand",
             "You act first and reason afterwards. Energy is never your problem; "
             "holding one line long enough to finish it is.",
             "neutral", "Pick one thing this month and refuse to start a second "
             "until it is done. A fire hand loses more to abandonment than to "
             "failure."),
    "water": ("a long palm with long fingers — a water hand",
              "You read a room before anybody speaks. Feeling arrives before "
              "reasoning does, and other people's moods stick to you.",
              "neutral", ""),
}

_THUMB_WILL = {
    "will_dominant": ("a thumb whose top section is the longer of the two",
                      "Will runs ahead of reasoning. Once you have decided, you "
                      "are very hard to move — which serves you until the "
                      "decision was the wrong one.",
                      "neutral",
                      "Before any big commitment, make yourself say out loud the "
                      "one argument against it. A will-led thumb rarely hears it "
                      "otherwise."),
    "logic_dominant": ("a thumb whose lower section is the longer of the two",
                       "Reasoning runs ahead of will. You see the right course "
                       "clearly and early, and then take longer than you should "
                       "to act on it.",
                       "care",
                       "Give yourself a deadline for deciding, not for finishing. "
                       "The delay in a logic-led thumb sits at the decision, not "
                       "at the work."),
    "balanced": ("a thumb whose two sections are near equal",
                 "You think and act in step — the balance the books call the "
                 "governing thumb.", "strong", ""),
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
        out.append(_mk("thumb_long", "Thumb length", "a long thumb",
                       "Command comes naturally. You end up running things you "
                       "only meant to help with.", tone="strong", hand=hand))
    elif length == "short":
        out.append(_mk(
            "thumb_short", "Thumb length", "a short thumb",
            "You lead with the heart rather than with authority. You will give "
            "way in an argument you were winning, then feel the cost of it later.",
            tone="care", hand=hand,
            remedy="Decide your limit before the conversation starts, and say it "
                   "in the first minute. A short thumb concedes late, not early."))

    opening = _val(thumb, "opening")
    if opening == "wide":
        out.append(_mk("thumb_open", "Thumb angle", "a wide-set thumb",
                       "Generous and open-handed. You are the one who pays, "
                       "helps, and is occasionally taken for granted for it.",
                       tone="neutral", hand=hand))
    elif opening in ("narrow", "close"):
        out.append(_mk(
            "thumb_closed", "Thumb angle", "a close-set thumb",
            "You hold things close — money, plans and feeling alike. The books "
            "call it caution, and it protects you more often than it costs you.",
            tone="neutral", hand=hand))

    idx = _val(morph, "index_vs_ring")
    if idx == "index_longer":
        out.append(_mk("index_long", "Your index finger",
                       "an index finger longer than your ring finger",
                       "You want to be in charge, and you feel it when you are "
                       "not. Working under someone you do not respect wears you "
                       "down faster than overwork does.", tone="neutral",
                       hand=hand))
    elif idx == "ring_longer":
        out.append(_mk("ring_long", "Your ring finger",
                       "a ring finger longer than your index finger",
                       "You take risks the cautious hand will not, and you read "
                       "an audience well. Recognition matters to you more than "
                       "rank does.", tone="neutral", hand=hand))
    return out


# ---------------------------------------------------------------------------
# the four major lines
# ---------------------------------------------------------------------------
_LIFE = {
    "depth": {
        "deep": ("runs deep and clearly cut",
                 "A strong constitution. You recover from illness, overwork and "
                 "bad years faster than the people around you, and you underrate "
                 "that because it has always been true.", "strong", ""),
        "medium": ("runs at an even, moderate depth",
                   "Steady vitality rather than an athlete's reserve. You have "
                   "enough for a full life, provided you do not spend three days "
                   "of it in one.", "neutral", ""),
        "shallow": ("runs fine and lightly marked",
                    "The books read a light life line as a nervous, quickly-spent "
                    "energy. You tire before you notice you are tiring.", "care",
                    "Guard your sleep before you guard your calendar. On this "
                    "line rest is the remedy, not a reward for finishing."),
    },
    "sweep": {
        "wide": ("sweeps wide around the ball of the thumb",
                 "Warmth, appetite and physical courage. You want people, food, "
                 "travel and movement in your life, not just work in it.",
                 "strong", ""),
        "narrow": ("hugs close to the thumb",
                   "Energy is held in rather than spent outward. Home and a "
                   "small circle restore you; crowds drain you.", "neutral", ""),
    },
    "quality": {
        "broken": ("shows a break",
                   "A break on the life line marks a change of place or of "
                   "circumstance, not an ending — classically a move, an illness "
                   "recovered from, or a life rearranged around new terms.",
                   "care",
                   "Treat the years around this break as a rebuilding stretch. "
                   "Do not sign anything long and rigid inside it."),
        "chained": ("is chained in places",
                    "Chaining is read as a run of small drains rather than one "
                    "large trouble — the years where health and mood keep "
                    "interrupting the work.", "care",
                    "Fix the small recurring thing you have been postponing. On a "
                    "chained line it is what is costing you the year."),
        "islanded": ("carries an island",
                     "An island on the life line marks a stretch of divided "
                     "strength — a period where health or circumstance takes a "
                     "share of what you meant to spend elsewhere.", "care",
                     "Book the check-up you have been putting off, and lighten "
                     "the load either side of this window rather than inside it."),
    },
}

_HEAD = {
    "depth": {
        "deep": ("is deeply cut",
                 "Concentration is your real gift. You hold one problem until it "
                 "gives way, and you think before you speak more often than the "
                 "people around you realise.", "strong", ""),
        "shallow": ("is lightly marked",
                    "Attention moves quickly and does not always come back. "
                    "Ideas arrive well; finishing them is the work.", "care",
                    "Write the decision down before you act on it. A light head "
                    "line loses good thinking to memory, not to error."),
    },
    "length": {
        "long": ("runs long across the palm",
                 "You think a thing all the way through. You are the one who "
                 "sees the consequence three steps out, which is why you are "
                 "slower to commit than the people asking you to.", "strong", ""),
        "short": ("stops short of the far side of the palm",
                  "You decide fast and directly. The books call it a practical "
                  "mind — it wants the answer, not the whole map.", "neutral",
                  ""),
    },
    "direction": {
        "moon": ("slopes down towards the outer edge of the palm",
                 "Imagination runs into your reasoning. You solve things "
                 "sideways, and you need creative work in your life or the "
                 "imagination turns on you and becomes worry.", "neutral",
                 "Keep one channel for imagination outside your job. On this "
                 "slope an unused imagination becomes anxiety."),
        "straight": ("runs straight across",
                     "A practical, literal mind. You want the plain facts and "
                     "you dislike being managed with atmosphere.", "neutral", ""),
        "upward": ("rises towards the little finger at its end",
                   "A head line curving up to Mercury is the trader's line — "
                   "money, negotiation and opportunity read clearly to you.",
                   "strong", ""),
    },
    "start_relation": {
        "merged": ("stays joined to the life line for a long start",
                   "Caution learned early. The books read a long join as a "
                   "childhood where family opinion carried real weight, and a "
                   "confidence that had to be built rather than assumed. It also "
                   "means you look before you leap, and that has saved you more "
                   "than once.", "care",
                   "Make one decision this month without asking anybody first. "
                   "On a long join, confidence returns through practice, not "
                   "through feeling ready."),
        "separate": ("leaves the life line cleanly at the start",
                     "Independence early. You made your own calls young, and you "
                     "still dislike being asked to justify them.", "strong", ""),
        "wide": ("starts well clear of the life line",
                 "A wide gap is read as impatience and self-trust in equal "
                 "measure. You move before you are ready, and mostly it works.",
                 "neutral",
                 "Give any irreversible decision one night. That single delay is "
                 "the whole correction this hand needs."),
    },
    "quality": {
        "broken": ("shows a break",
                   "A break on the head line marks a change of mind big enough to "
                   "change a life — a course abandoned, a field changed, a belief "
                   "put down.", "care",
                   "Around that stretch, keep decisions reversible for a season."),
        "islanded": ("carries an island",
                     "An island here is read as a period of divided attention — "
                     "worry, strain, or two demands running at once.", "care",
                     "Take the second thing off your plate before this window, "
                     "not during it."),
        "chained": ("is chained in places",
                    "Chaining on the head line is the classical mark of scattered "
                    "concentration and mental fatigue.", "care",
                    "Protect one hour a day with nothing in it. Chaining answers "
                    "to rest faster than to effort."),
    },
}

_HEART = {
    "depth": {
        "deep": ("is deeply cut",
                 "You feel strongly and you love without a reserve tank. When "
                 "you are in, you are entirely in — and you expect the same, "
                 "which not everyone can give.", "strong", ""),
        "shallow": ("is lightly marked",
                    "Feeling is real but held back from the surface. People read "
                    "you as cooler than you are.", "care",
                    "Say the warm thing out loud once. On a light heart line the "
                    "affection is felt but not received."),
    },
    "start_zone": {
        "jupiter": ("begins under the index finger",
                    "The idealist's heart line. You love the whole person and "
                    "you set a high bar — and you are hurt properly when it is "
                    "not met.", "neutral", ""),
        "saturn": ("begins under the middle finger",
                   "A reserved, serious attachment. The books read this start as "
                   "affection that is physical and practical rather than "
                   "demonstrative — you show love by what you do, not by what "
                   "you say.", "neutral",
                   "Put the feeling into words once, not only into actions. "
                   "Partners on this line complain of silence far more often "
                   "than of coldness."),
        "between": ("begins between the index and middle fingers",
                    "The balanced start — you give and expect in fair measure, "
                    "and you recover from a disappointment without closing.",
                    "strong", ""),
    },
    "length": {
        "short": ("is short",
                  "Affection is focused on a few people rather than spread wide. "
                  "The circle is small on purpose.", "neutral", ""),
        "long": ("runs long across the palm",
                 "You attach deeply and you hold on. Letting go of a person, or "
                 "of a version of a person, takes you longer than it takes most.",
                 "neutral", ""),
    },
    "quality": {
        "broken": ("shows a break",
                   "A break on the heart line is the classical mark of a "
                   "significant emotional turn — a parting, or a loyalty that "
                   "changed shape.", "care",
                   "Around this stretch, say the difficult thing early. On this "
                   "line the damage is done by what goes unsaid."),
        "chained": ("is chained across part of its run",
                    "Chaining on the heart line reads as unsettled affection — "
                    "several attachments, or one that keeps re-negotiating "
                    "itself.", "care",
                    "Decide what you actually want from the relationship before "
                    "the next conversation about it."),
        "islanded": ("carries an island",
                     "An island here marks a period of divided feeling.", "care",
                     "Do not make the permanent decision inside this window."),
    },
}

_FATE = {
    "depth": {
        "deep": ("runs strong and clear",
                 "A real vocation, not just a job. Effort converts into position "
                 "for you where other hands have to keep starting over.",
                 "strong", ""),
        "shallow": ("runs faintly",
                    "The path is being made rather than inherited. Direction "
                    "arrives late on this line, and usually through one person "
                    "or one opening rather than through a plan.", "neutral", ""),
    },
    "start_zone": {
        "wrist": ("rises from the wrist",
                  "Direction was set early. You have known roughly what you were "
                  "for since you were young.", "strong", ""),
        "mid_palm": ("rises from the middle of the palm",
                     "Your vocation clarifies in the middle of life rather than "
                     "at the start of it. The books put this start at the age "
                     "where a person stops doing what was expected and starts "
                     "doing what fits.", "neutral", ""),
        "moon": ("rises from the outer edge of the palm",
                 "A career made through other people — clients, audiences, the "
                 "public. Your openings come through who notices you, so the "
                 "network is not a distraction from the work, it is the work.",
                 "neutral", ""),
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
        out.append(_mk(f"mark_{kind}_{zone}", title, sign, meaning, tone=tone,
                       remedy=_MARK_REMEDY.get(kind, ""), hand=hand, where=where))
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
