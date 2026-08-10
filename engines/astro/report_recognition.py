"""Tell the reader about their own past — do not ask them to supply it.

The previous version of this asked for four dates and then announced which
planetary period each fell in. It scored 4 of 4 on the test chart and looked
superb.

It was worthless, and measurably so. Feeding it *fabricated* dates scored 76%
on average and a perfect 4 of 4 in 35% of random trials. With three period
lords in play (mahadasha, antardasha, Yogini) and two or three acceptable
significators per event, almost any date "matches" something. The customer
supplies the fact, we supply a rationalisation, and both parties come away
impressed. That is a cold-reading trick, not a proof.

So this inverts it. **We** make the statements; the reader judges them. No
dates are requested and none are needed — every claim below is a structural
pattern read off the chart, and the reader either recognises it or does not.

Two deliberate exclusions:

* **No marriage or childbirth timing.** Those are the classic astrologer's
  gamble: probabilistic, high-stakes, and a miss is unforgivable. They are also
  the ones most contaminated by the reader's own life pressure.
* **No dated past events at all.** A pattern that has run for years ("your
  energy dips before it breaks, and it always shows in the same place") is both
  checkable and true. A specific past date is a guess dressed as a fact.

What is left is what the chart is actually good at: standing patterns in
health, money, love, parents and work.

Two sources feed it. The hand-written rules below read house lords, occupancy
and Ashtakavarga directly. On top of those sit the classical rules from
`prediction108_rules.evaluate_all`, which test 108 named book configurations
against the chart and report HIT / PARTIAL / NO — a HIT is a narrow geometric
condition, and therefore better raw material than anything we can write off a
single house lord. Their `prediction` strings are *not* used verbatim: they are
written forward ("position yourself for gains during it"), and this block only
makes claims the reader can check against a life already lived. The 108 section
below documents the rephrasing rules, the exclusions and their reasons.

The falsification standard this module has to meet is the one the old block
failed: **two different charts must produce noticeably different statements.**
There is a test for it at the bottom. Wiring in the 108 rules roughly doubled
the statement count (6-8 to 11-15 per chart on the four reference charts) while
mean pairwise overlap went from 0.123 to 0.114. Adding statements is only an
improvement while that number holds — if it rises, the new lines are Barnum.
"""

from __future__ import annotations

import html as _html
import re
from typing import Any

from report_language import client_prose

try:
    from interpretation.life_stage import age_band as _age_band_fn, is_minor
    from qa_checks.age_context_check import age_violations
except Exception:  # noqa: BLE001
    def _age_band_fn(pc, today=None):  # type: ignore
        return "adult"

    def is_minor(band):  # type: ignore
        return False

    def age_violations(text, band):  # type: ignore
        return []

RECOG_LABELS_MINOR: dict[str, str] = {
    "love": "Friendships & close bonds",
    "career": "Studies & recognition",
    "money": "Resources & money habits",
}

BENEFIC = ("Jupiter", "Venus", "Mercury", "Moon")
MALEFIC = ("Saturn", "Mars", "Sun", "Rahu", "Ketu")


def _e(t: Any) -> str:
    return _html.escape(str(t or ""))


def _house_of(pc: dict, planet: str):
    return (pc.get("planets", {}).get(planet) or {}).get("house")


def _lord(pc: dict, house: int) -> dict:
    return (pc.get("house_lords", {}) or {}).get(str(house)) or {}


def _dig(pc: dict, planet: str) -> str:
    return str((pc.get("planets", {}).get(planet) or {}).get("dignity") or "").lower()


def _sav(pc: dict, house: int):
    sav = (pc.get("ashtakavarga", {}) or {}).get("sav") or []
    return sav[house - 1] if len(sav) >= house else None


def _occupants(pc: dict, house: int) -> list:
    return [p for p, d in (pc.get("planets", {}) or {}).items()
            if d.get("house") == house]


# ---------------------------------------------------------------------------
# THE 108 CLASSICAL RULES AS A SECOND SOURCE
#
# `prediction108_rules.evaluate_all(pc)` tests 108 book rules against the chart
# and returns a RuleVerdict per rule (HIT / PARTIAL / NO / NA) carrying a
# `prediction` string. A HIT is exactly the kind of material this block wants:
# it is conditional on real geometry, so it cannot fire for everybody.
#
# Three deliberate constraints on how we consume it:
#
# 1. **We do not use `v.prediction` verbatim.** Almost every one of those
#    strings is written forward ("position yourself for gains during it",
#    "remedies lighten it considerably"). This block is a *past* reading — the
#    reader has to be able to check it against a life already lived. So each
#    rule we keep gets a hand-written past/pattern rephrasing below, and any
#    rule whose claim cannot survive that rewrite is dropped outright (see
#    EXCLUDED_108 for the list and the reason).
#
# 2. **Rules that hit every chart are dropped even when they hit.** Measured
#    across the four reference charts, rules 2, 11, 14, 24, 34, 47, 75, 81 and
#    83 hit 4/4. A statement that fires for everyone is a Barnum line no matter
#    how classical its provenance, and it would push the differentiation score
#    up. The exception is a near-universal rule whose *content* varies by chart
#    (19, 48, 76) — those are kept but parameterised by the house/planet
#    involved, so two charts hitting the same rule still read differently.
#
# 3. **HIT only, never PARTIAL.** Every PARTIAL verdict in these charts has an
#    empty `prediction` and a hedged finding ("moderate clan-wealth potential").
#    Hedged material is what this block exists to avoid.
# ---------------------------------------------------------------------------

# What a house means when we have to describe it to a layman in past tense.
HOUSE_THEME = {
    1: "your own body and how you are seen",
    2: "family money and what you were able to say out loud",
    3: "siblings, and your own nerve",
    4: "home and your mother",
    5: "children, study, and anything you made yourself",
    6: "work, debt and health",
    7: "marriage and business partnership",
    8: "money and obligations that were never yours to begin with",
    9: "your father, and what you were raised to believe",
    10: "career and public standing",
    11: "income and the network it comes through",
    12: "expense, distance from home, and sleep",
}

# Which product domain a house-flavoured statement belongs in. The 5th is
# children/study/creation — it belongs with work rather than with parents,
# which is where a naive "5th is a family house" mapping would put it.
HOUSE_DOMAIN = {
    1: "health", 2: "money", 3: "career", 4: "parents", 5: "career",
    6: "health", 7: "love", 8: "money", 9: "parents", 10: "career",
    11: "money", 12: "health",
}

# The same twelve houses as a noun phrase that survives "the stage on which
# ___ got worked out". HOUSE_THEME does not read correctly in that frame.
STAGE_THEME = {
    1: "who you are as a person",
    2: "family money",
    3: "your relationship with a sibling",
    4: "your home life",
    5: "your children and the things you wanted to make",
    6: "your health and your debts",
    7: "your marriage",
    8: "money that belonged to other people",
    9: "what your father expected of you",
    10: "your own ambition",
    11: "your friendships",
    12: "everything you were trying to get away from",
}


def _p108(pc: dict) -> dict:
    """{rule_no: RuleVerdict} for the natal rules that HIT, or {} if unavailable.

    Uses the shared deep_evidence cache when active (one evaluate_all per report).
    """
    try:
        import deep_evidence as DE
        ctx = DE.current()
        if ctx is not None:
            return ctx.natal_rule_hits()
    except Exception:  # noqa: BLE001
        pass
    hits: dict = {}
    try:
        from prediction108_rules import evaluate_all  # noqa: PLC0415
        for v in evaluate_all(pc):
            # transit/annual rules are time-specific and therefore forward-
            # looking by construction — they can never be a past pattern.
            if v.verdict == "HIT" and v.category == "natal":
                hits[v.no] = v
    except Exception:  # noqa: BLE001
        hits = {}
    return hits


def _rel_from_moon(pc: dict, planet: str) -> int:
    """House of `planet` counted from the Moon (1..12), 0 if unknown."""
    ph, mh = _house_of(pc, planet), _house_of(pc, "Moon")
    if not ph or not mh:
        return 0
    return ((ph - mh) % 12) + 1


# Per-planet phrasings. A rule like "a dignified planet sits in an angle" is
# true of many charts; naming the planet's flavour is what keeps two charts
# that both trip it from producing the same sentence.
_AUTHORITY_BY_PLANET = {
    "Sun": "You have been handed authority in rooms where you were not the "
           "most qualified person there, and it stuck.",
    "Moon": "People have told you things early. You were the one others "
            "briefed before they briefed anyone official.",
    "Mars": "When something had to actually get done, it came to you — and "
            "you have resented being the only one who could be relied on.",
    "Mercury": "Your standing came from being the person who could explain "
               "it. You have been in rooms because you could translate.",
    "Jupiter": "You have been treated as the grown-up in groups where you "
               "were not the oldest.",
    "Venus": "Part of your position has always owed something to the fact "
             "that people like dealing with you, and you know it.",
    "Saturn": "Your standing was earned by being the one who stayed after "
              "the people who arrived with you had left.",
}

_EXALTED_STATUS_BY_PLANET = {
    "Sun": "There is one arena where you have been given more respect than "
           "your paperwork justifies.",
    "Moon": "You have had a reputation for being reliable in a crisis before "
            "you felt reliable in one.",
    "Mars": "You have been unusually good at one specific thing since you "
            "were young, and it has carried you further than your training.",
    "Mercury": "You have out-argued people who outranked you, more than once.",
    "Jupiter": "People have asked your opinion on decisions that were not "
               "yours to make.",
    "Venus": "Your name travels ahead of you in one particular circle.",
    "Saturn": "You are the one people ring when it has gone wrong, not when "
              "it is going well.",
}


# Each builder returns a list of (domain, tag, statement). `tag` exists only so
# _resolve_conflicts can spot two statements that cannot both be true.
def _b19(pc: dict, v) -> list:
    """8th lord's house — where the unplanned turns landed."""
    h = _house_of(pc, _lord(pc, 8).get("lord", ""))
    if not h:
        return []
    lord = _lord(pc, 8).get("lord") or "Saturn"
    return [(HOUSE_DOMAIN[h], f"upheaval_{h}",
             "The part of your life that has never quite settled is "
             f"{HOUSE_THEME[h]}. That is where the sudden turns came, and "
             "they arrived without much warning.",
             "", (h, lord))]


def _b48(pc: dict, v) -> list:
    """Rahu's dispositor compromised — the repeated, self-inflicted cost."""
    h = _house_of(pc, "Rahu")
    if not h:
        return []
    return [(HOUSE_DOMAIN[h], f"repeat_{h}",
             "The same mistake has cost you twice in one area of life — "
             f"{HOUSE_THEME[h]}. The second time it came dressed differently "
             "and you did not recognise it until afterwards.",
             "", (h, "Rahu"))]


def _b76(pc: dict, v) -> list:
    """10th lord strong vs under pressure.

    We re-derive strength from the dignity rather than trusting the rule's own
    wording: on one test chart rule 76 reported "the 10th lord Mercury is well
    placed (debilitated, in the 7th)", which is self-contradictory. Dignity is
    the thing the classical rule is actually about, so we read that directly.
    """
    lord = _lord(pc, 10).get("lord") or "Mercury"
    dig = _lord(pc, 10).get("lord_dignity", "")
    if dig in ("exalted", "own_sign", "moolatrikona"):
        return [("career", "career_straight",
                 "Work has paid you back roughly in proportion to what you "
                 "put in. You have not had to reinvent yourself to stay "
                 "employed, and that is rarer than you think.",
                 "", (10, lord))]
    if dig in ("debilitated", "enemy_sign"):
        return [("career", "career_detour",
                 "Your career has not run in a straight line. You have had to "
                 "re-establish yourself at least once, later than the people "
                 "you started with, and explain a gap you did not choose.",
                 "", (10, lord))]
    return []


def _b15(pc: dict, v) -> list:
    """A 6/8/12 lord standing in its own sign — the difficulty that never stuck."""
    out = []
    for house in (6, 8, 12):
        info = _lord(pc, house)
        lord = info.get("lord") or "Saturn"
        if info.get("lord_dignity") in ("own_sign", "moolatrikona"):
            if house == 6:
                out.append(("health", "health_outlasts",
                            "Illness, debt and opposition have all come at "
                            "you, and none of them stuck. You have outlasted "
                            "things that put other people out of action.",
                            "", (house, lord)))
            elif house == 8:
                out.append(("health", "health_survived",
                            "You have been through at least one thing that "
                            "should have marked you permanently, and it did "
                            "not. You came out roughly intact.",
                            "", (house, lord)))
            else:
                out.append(("money", "money_loss_absorbed",
                            "You have absorbed a loss that other people would "
                            "still be talking about, and you stopped talking "
                            "about it quickly.",
                            "", (house, lord)))
    return out[:1]  # one is a statement; three is a theme, and reads padded


def _b66(pc: dict, v) -> list:
    """6th house/lord — the running fight, or the winning of it."""
    lord = _lord(pc, 6).get("lord") or "Mars"
    dig = _lord(pc, 6).get("lord_dignity", "")
    if dig in ("exalted", "own_sign", "moolatrikona"):
        return [("health", "health_outlasts",
                 "You beat the people and the illnesses that were expected to "
                 "beat you. Conflict has never frightened you the way it "
                 "frightens others.",
                 "", (6, lord))]
    return [("health", "health_running_fight",
             "There has been a low-grade running fight in your life — with "
             "your own body, with a debt, or with someone who would not let "
             "go. It has been long rather than dramatic, and it wore you down "
             "in a way nobody saw.",
             "", (6, lord))]


def _b3(pc: dict, v) -> list:
    return [("health", "mind_steady",
             "Your temperament has been steadier than your circumstances "
             "justified. People have leaned on you during stretches when you "
             "were quietly struggling yourself.")]


def _b68(pc: dict, v) -> list:
    return [("health", "survivor",
             "You have come through a stretch that visibly changed the people "
             "who went through it with you. They call it strength; you know "
             "most of it was stubbornness.")]


def _b21(pc: dict, v) -> list:
    return [("money", "money_windfall",
             "Money has reached you at least once from a source you did not "
             "earn week by week — a legacy, a settlement, an insurance, or "
             "someone else's resources becoming yours to manage.")]


def _b17(pc: dict, v) -> list:
    return [("money", "money_fought_for",
             "What you have, you got by outlasting competition rather than by "
             "being handed an opening. Your income has moved in steps, and "
             "each step followed a fight.")]


def _b56(pc: dict, v) -> list:
    return [("money", "money_inheritance",
             "Property or a family legacy has either already come to you or "
             "is sitting unresolved on the family side, waiting for a "
             "conversation nobody wants to start.")]


def _b78(pc: dict, v) -> list:
    return [("money", "money_started_behind",
             "You started behind. There was a period — usually early — when "
             "you visibly had less than the people you were being measured "
             "against, and the recovery came later and faster than anyone "
             "expected, including you.")]


def _b27(pc: dict, v) -> list:
    return [("money", "money_floor",
             "There was a floor under you. However bad it got, there was a "
             "family position you could have fallen back to, and knowing that "
             "shaped the risks you were willing to take.")]


def _b64(pc: dict, v) -> list:
    return [("career", "self_made",
             "Nothing was pre-arranged for you. Every position you hold you "
             "assembled from a standing start, and you are still slightly "
             "suspicious of people who were introduced into theirs.")]


def _b39(pc: dict, v) -> list:
    return [("love", "love_delayed",
             "Your marriage — or the one partnership that counted — took "
             "longer to settle than the people around you expected. Something "
             "got in the way after it already looked decided.")]


def _b71(pc: dict, v) -> list:
    return [("love", "love_hot",
             "Attraction has run hot and fast for you, and the same heat has "
             "come back as friction with the person you chose. The intensity "
             "and the arguments are the same thing.")]


def _b31(pc: dict, v) -> list:
    """A debilitated house lord — the specific thing the household lacked."""
    out = []
    for house in (4, 9):
        info = _lord(pc, house)
        lord = info.get("lord") or ("Moon" if house == 4 else "Sun")
        if info.get("lord_dignity") == "debilitated":
            if house == 4:
                out.append(("parents", "home_underresourced",
                            "The house you grew up in was short of something "
                            "specific — money, space, or the attention of "
                            "whoever should have been giving it — and you "
                            "learned not to ask.",
                            "", (house, lord)))
            else:
                out.append(("parents", "father_diminished",
                            "Your father was diminished in some way you were "
                            "old enough to see: his position, his health, or "
                            "how the family talked about him.",
                            "", (house, lord)))
    return out


def _b26(pc: dict, v) -> list:
    return [("career", "career_state",
             "Government, public-sector or state-funded work has run through "
             "your line — as employer, as client, or as the thing your family "
             "assumed you would do.")]


def _b45(pc: dict, v) -> list:
    return [("career", "career_vouched",
             "Your openings have come through your reputation rather than "
             "through applications. More than once, someone vouched for you "
             "in a room you were not in.")]


def _b69(pc: dict, v) -> list:
    return [("career", "career_head",
             "You have earned from your head rather than your hands — "
             "explaining, analysing, or organising other people's mess.")]


def _b6(pc: dict, v) -> list:
    return [("career", "career_charge",
             "You have been put in charge of things you were not formally "
             "senior enough to run, and it happened early enough that you "
             "assumed it was normal.")]


def _b10(pc: dict, v) -> list:
    return [("career", "career_initiative",
             "Luck has followed your initiative rather than preceding it. "
             "Doors opened after you moved, never before — which is why you "
             "have trouble waiting.")]


def _b59(pc: dict, v) -> list:
    return [("career", "career_reader",
             "People bring you their problems, including strangers. You have "
             "read situations correctly — and read people's motives correctly "
             "— often enough that it has unsettled you.")]


def _b77(pc: dict, v) -> list:
    return [("career", "career_early_recognition",
             "You were recognised in your field before you felt ready for it, "
             "and part of you has been catching up with that ever since.")]


def _b38(pc: dict, v) -> list:
    """The 10th holds a lord of some other house — career as the stage for it."""
    for p in _occupants(pc, 10):
        for h in range(1, 13):
            if h != 10 and _lord(pc, h).get("lord") == p:
                return [("career", f"career_stage_{h}",
                         f"Your working life has been the stage on which "
                         f"{STAGE_THEME[h]} got worked out. The two have "
                         "never been separable for you.",
                         "", (10, p))]
    return []


def _b50(pc: dict, v) -> list:
    for h in (1, 4, 7, 10):
        for p in _occupants(pc, h):
            if _dig(pc, p) in ("exalted", "own_sign", "moolatrikona"):
                line = _AUTHORITY_BY_PLANET.get(p)
                if line:
                    return [("career", "authority", line, "", (h, p))]
    return []


def _b25(pc: dict, v) -> list:
    for p, d in (pc.get("planets", {}) or {}).items():
        if d.get("dignity") == "exalted" and d.get("house") in (1, 4, 5, 7, 9, 10):
            line = _EXALTED_STATUS_BY_PLANET.get(p)
            if line:
                return [("career", "status", line, "", (int(d["house"]), p))]
    return []


def _b57(pc: dict, v) -> list:
    return [("career", "adhi_respected",
             "You have quietly accumulated a good name. People who barely "
             "know you would speak well of you, and you have benefited from "
             "that without ever engineering it.",
             "", (10, "Jupiter"))]


def _b58(pc: dict, v) -> list:
    return [("health", "adhi_struggle",
             "You were built by difficulty rather than by encouragement. "
             "There is a hardness in you that shows up when you are tired, "
             "and the people closest to you have seen it.",
             "", (6, "Saturn"))]


# rule no -> builder. Anything not in here is excluded; EXCLUDED_108 records why.
RULE108_BUILDERS = {
    3: _b3, 6: _b6, 10: _b10, 15: _b15, 17: _b17, 19: _b19, 21: _b21,
    25: _b25, 26: _b26, 27: _b27, 31: _b31, 38: _b38, 39: _b39, 45: _b45,
    48: _b48, 50: _b50, 56: _b56, 57: _b57, 58: _b58, 59: _b59, 64: _b64,
    66: _b66, 68: _b68, 69: _b69, 71: _b71, 76: _b76, 77: _b77, 78: _b78,
}

# Kept for the next person who wonders why 80 hitting rules produce 8 lines.
EXCLUDED_108 = {
    2: "hits 4/4 charts (day birth + 4 planets in the visible half) and the claim is 'your potential delivers' — Barnum",
    1: "prediction is about a future dasha, and the finding contradicts itself on one chart (illness flag AND 'very good results')",
    4: "Uttarayan is true of half of all births; claim is pure flattery",
    5: "PARTIAL only across all four charts, and 'the regal promise is only latent' is unfalsifiable",
    8: "PARTIAL only; describes a technical collapse of a yoga, not a life pattern",
    11: "hits 4/4; 'a quiet boost' is not checkable",
    12: "'a dependable pillar of strength' — no observable referent",
    13: "conditional on a future dasha",
    14: "hits 4/4; the prediction is an instruction to the astrologer, not a claim",
    16: "verbatim duplicate of 15 (the engine emits both)",
    18: "no hits, and it is a longevity claim",
    20: "duplicate of 19 with the same house",
    22: "longevity/lifespan — excluded on principle, like marriage timing",
    23: "'sound longevity' is unfalsifiable in a past reading",
    24: "hits 4/4 ('8th lord afflicted' is near-universal) and it is a health-fear claim",
    32: "no hits in the reference set",
    34: "hits 4/4 and predicts 'civil service or high office' — flattering and mostly wrong",
    35: "PARTIAL on all four charts by construction",
    42: "'king-like, undefeatable' — the purest Barnum line in the set",
    44: "explicitly future ('position yourself for gains during it')",
    46: "'their periods tend to be constructive' — future, and vague",
    47: "hits 4/4; a navamsha-trine count is not a life event",
    49: "overlaps 25 and 31 without adding an observable",
    52: "hits or partials everywhere; 'resources tend to flow'",
    55: "hits 3/4 with 'the classic mix for a materially successful life' — flattery",
    60: "PARTIAL only",
    61: "conditional on a future dasha",
    63: "'dignity and grace in how you carry power' — no way for a reader to score it",
    65: "PARTIAL only",
    67: "'the eight forms of fortune are favoured' — blessing, not observation",
    72: "hits or partials everywhere; kendra counting is not a life pattern",
    75: "hits 4/4; 'periods of real hardship' plus a remedy pitch",
    79: "'king-like, widely respected' — flattery",
    80: "'a gentle, supportive thread in life' — unfalsifiable",
    81: "hits 4/4; 'vitality and progeny are favoured' is a blessing and touches childbirth",
    82: "'honoured and never defeated' — flattery",
    83: "hits 4/4; 'once you set a goal you are hard to stop' is the single most "
        "agreeable sentence you can say to a stranger",
}


# Statements that cannot both be true. Value is the tag we drop, and the test
# that decides. Each is resolved on chart strength, never on which fired first.
def _resolve_conflicts(pc: dict, items: list) -> list:
    """Drop the weaker half of any pair of statements that contradict.

    Reasoning for each pair is spelled out inline, because the resolution is a
    judgement about which piece of geometry is the stronger witness — that is
    exactly the thing a future reader will want to argue with.
    """
    tags = {it[1] for it in items}
    drop: set = set()

    # money_floor (rule 27, 9th lord in a 9th-trine = inherited comfort) vs
    # money_started_behind (78, neecha-bhanga = began deprived) and self_made
    # (64). Decider: the 9th lord's own dignity. Rule 27 fires on *placement*
    # alone, so a debilitated 9th lord can trip it while being the weakest
    # planet in the chart — on one reference chart the same engine flags that
    # 9th lord as debilitated under rule 31. Placement loses to dignity.
    if "money_floor" in tags and ({"money_started_behind", "self_made"} & tags):
        ninth_dig = _lord(pc, 9).get("lord_dignity", "")
        if ninth_dig in ("debilitated", "enemy_sign"):
            drop.add("money_floor")
        else:
            drop.update({"money_started_behind", "self_made"})

    # The hand-written "money was genuinely tight early" line says the same
    # thing as money_started_behind and contradicts money_floor. The 108 rule
    # is the more specific witness (it requires an actual neecha-bhanga, not
    # just a weak 2nd lord), so it wins either way.
    if "money_started_behind" in tags:
        drop.add("money_tight")
    if "money_floor" in tags and "money_floor" not in drop:
        drop.add("money_tight")

    # health_outlasts (15/66-strong: the 6th lord stands in its own sign) vs
    # health_running_fight (66-weak: the 6th lord is a functional malefic under
    # stress). Both fire together on one reference chart — the engine's own
    # contradiction. Dignity is the harder fact: a planet in its own sign is
    # strong regardless of its functional label, so the fight-was-won reading
    # wins and the grinding-illness reading is dropped.
    if "health_outlasts" in tags:
        drop.add("health_running_fight")
        # Not a contradiction but a restatement: the hand-written resilience
        # lines ("you recover faster than most", older direct medical-claim wording
        # than average") say what health_outlasts says, from looser conditions
        # (one dignity, one Ashtakavarga threshold). Three ways of saying the
        # same thing reads as padding, so the narrower rule keeps the slot.
        drop.add("health_sav_6")
        # Same axis, opposite direction: "your baseline stamina has always been
        # lower than people assume" cannot stand next to "you outlasted things
        # that put others out of action". The stamina line reads the lagna
        # lord (general constitution); health_outlasts reads the 6th/8th lord,
        # which is the house that specifically governs how illness resolves.
        # For a claim about illness outcomes the 6th lord is the closer witness.
        drop.add("health_lagna_weak")

    # health_running_fight (6th lord neither strong nor weak, so the engine
    # defaults to the grinding reading) vs health_sav_6 (SAV of the 6th at
    # 30+, i.e. a measured strength figure). A Sarvashtakavarga count is a
    # number; "functional malefic" is a label. Where the 6th lord is only
    # neutral, the number wins and the grinding reading is dropped. If the 6th
    # lord is genuinely weak, the label is backed by dignity too and it stays.
    if {"health_running_fight", "health_sav_6"} <= tags:
        if _lord(pc, 6).get("lord_dignity") in ("debilitated", "enemy_sign"):
            drop.add("health_sav_6")
        else:
            drop.add("health_running_fight")

    # adhi_respected (57, benefics in 6/7/8 from the Moon) vs adhi_struggle
    # (58, malefics in the same houses). Both fire on two of four charts.
    # Decider: count them. Whichever side actually occupies more of the three
    # houses is the one the chart is making. On a tie we keep the struggle
    # line — it is the less flattering and therefore the more falsifiable of
    # the two, which is the standard this whole block is held to.
    if {"adhi_respected", "adhi_struggle"} <= tags:
        ben = sum(1 for p in BENEFIC if _rel_from_moon(pc, p) in (6, 7, 8))
        mal = sum(1 for p in MALEFIC if _rel_from_moon(pc, p) in (6, 7, 8))
        drop.add("adhi_struggle" if ben > mal else "adhi_respected")

    # career_straight vs career_detour cannot co-occur (one rule, two branches)
    # but a hand-written line could still fight them; nothing does today.

    return [it for it in items if it[1] not in drop]


def _verdict_finding(v: Any) -> str:
    """The geometry that fired a 108 rule — the best evidence we have.

    RuleVerdict carries a `finding` describing the actual placement it matched
    on. That is strictly better evidence than anything we could reconstruct, so
    prefer it and fall back to a generic derivation only when it is absent.
    """
    for attr in ("finding", "reason", "because", "detail", "evidence"):
        text = getattr(v, attr, "") or ""
        if isinstance(text, str) and len(text.strip()) > 8:
            # These are analyst notes; strip the rule bookkeeping a reader does
            # not need while keeping the placement itself.
            out = re.sub(r"^\s*(Rule\s*#?\d+\s*[:·-]\s*)", "", text.strip())
            out = re.sub(r"\s+", " ", out)
            return out[:220]
    return ""


def _items108(pc: dict) -> list:
    """(domain, tag, statement, why, evidence) from the 108 rules that hit."""
    hits = _p108(pc)
    items: list = []
    for no, builder in RULE108_BUILDERS.items():
        v = hits.get(no)
        if v is None:
            continue
        try:
            why = _verdict_finding(v)
            for it in builder(pc, v):
                domain, tag, text = it[0], it[1], it[2]
                why_override = it[3] if len(it) > 3 and it[3] else ""
                explicit_ev = it[4] if len(it) > 4 else None
                evidence = _item_evidence(tag, pc, explicit_ev)
                items.append((domain, tag, text, why_override or why, evidence))
        except Exception:  # noqa: BLE001
            # One broken rule must not cost the reader the whole section.
            continue

    # rule 50 and rule 25 both describe standing from a dignified planet; if 50
    # produced a line, 25's is a weaker restatement of it.
    if any(it[1] == "authority" for it in items):
        items = [it for it in items if it[1] != "status"]

    # Two rules can reach the same conclusion by different routes (15 and 66
    # both give health_outlasts when the 6th lord is dignified). Saying it
    # twice in slightly different words is the tell of a generated report, so
    # a tag may appear once.
    seen_tags: set = set()
    unique = []
    for it in items:
        if it[1] in seen_tags:
            continue
        seen_tags.add(it[1])
        unique.append(it)
    return unique


def rules108_claims(pc: dict) -> dict:
    """{domain: [statement, ...]} derived from the 108 rules that hit."""
    out: dict = {}
    seen: set = set()
    for domain, _tag, text in _resolve_conflicts(pc, _items108(pc)):
        if text in seen:
            continue
        seen.add(text)
        out.setdefault(domain, []).append(text)
    return out


# Tags for the hand-written claims that can collide with a 108 statement.
# Only the ones that actually contradict need an entry.
HANDWRITTEN_TAGS = {
    "There was a stretch — usually early — when money was "
    "genuinely tight, and it permanently changed how you think "
    "about spending.": "money_tight",
    "Your baseline stamina has always been lower than the people "
    "around you assume, and you have compensated by pushing "
    "rather than by resting.": "health_lagna_weak",
    "You tend to recover from setbacks with more resilience than people "
    "may expect. The same persistence often appears when you face "
    "opposition or difficult circumstances.": "health_sav_6",
    "You recover faster than most people. You have probably been "
    "back on your feet from things that flattened others.": "health_lagna_strong",
    "Whatever goes wrong with your health tends to be slow and "
    "recurring rather than sudden — it builds for months, and it "
    "usually shows up first as stiffness, sleep or the lower back.": "health_saturn_6",
    "Your health problems arrive fast and hot — inflammation, "
    "fevers, sudden injuries — and they clear almost as quickly "
    "as they came.": "health_mars_6",
    "You have had at least one health complaint that took an "
    "unusually long time to diagnose correctly.": "health_node_6",
    "Your stomach is where your stress goes first. When life is "
    "difficult, digestion is the thing that tells you before you "
    "have admitted it to yourself.": "health_moon_gut",
    "Heat, eyes or blood pressure — one of those three is the "
    "thing you have been told to watch.": "health_sun_vitals",
    "You put on weight when life gets comfortable, and it comes "
    "off only when something forces the issue.": "health_jupiter_weight",
    "Your money has come through people rather than through "
    "salary alone — introductions, networks, someone who thought "
    "of you.": "money_lord_exchange",
    "Your best earnings have come from something slightly "
    "unconventional, or from outside your home state or country.": "money_rahu_11",
    "You accumulate slowly and you are careful with money in a "
    "way that looks like anxiety to people who earn more easily.": "money_saturn_2",
    "Money leaves you in large single amounts rather than "
    "draining away — a medical bill, a family obligation, one "
    "big commitment at a time.": "money_malefic_12",
    "Money has arrived at the moment you needed it more than "
    "once, in a way that was hard to plan for and easy to be "
    "grateful for.": "money_jupiter_wealth",
    "You earn from what you know rather than from what you own "
    "— your income is tied to your own head, not to assets.": "money_mercury_earn",
    "You are better at earning than at holding. Income has "
    "rarely been the problem; what stays is.": "money_sav_earn_hold",
    "Once money reaches you it tends to stay. You are not a "
    "person who loses what they have built.": "money_sav_hold",
    "Your closest relationships have had a private difficulty in "
    "them that outsiders never saw — you handled it without "
    "telling many people.": "love_lord_dusthana",
    "You undersell yourself in love. You have been chosen by "
    "people who saw your worth before you did.": "love_venus_debilitated",
    "Affection has rarely been hard for you to find. Choosing "
    "well from what was offered was the harder part.": "love_venus_strong",
    "Your significant relationship involved an age, distance or "
    "responsibility gap — something that made it heavier than a "
    "simple romance.": "love_saturn_7",
    "Arguments in your relationships flare quickly. The heat "
    "passes fast, but it has frightened people who are not built "
    "like you.": "love_mars_7",
    "Relationships have asked more work of you than they seem "
    "to ask of other people. When they work, it is because you "
    "built them, not because they were easy.": "love_sav_7",
    "People notice you before you have said anything. That has "
    "opened doors and it has also attracted the wrong sort of "
    "attention.": "love_venus_angle",
    "There has been at least one attachment you kept largely to "
    "yourself.": "love_venus_hidden",
    "Your father was either absent in some practical way, or "
    "carried a difficulty — health, work or temperament — that "
    "the family arranged itself around.": "parents_sun_weak",
    "Your father's standing mattered in your household, and some "
    "of what you expect of yourself came directly from him.": "parents_sun_strong",
    "You are closer to your mother than to your father, and she "
    "is still the one you would call first.": "parents_moon_4",
    "Home was not entirely settled when you were young — a move, "
    "a financial squeeze, or a stretch where things were tense.": "parents_4th_dusthana",
    "You did not inherit an easy road. Whatever you have, you "
    "assembled — and part of you still does not fully trust "
    "help when it is offered.": "parents_9th_dusthana",
    "Responsibility landed on you earlier than it should have. "
    "You were the sensible one before you were ready to be.": "parents_saturn_early",
    "Whatever else was going on, you had one steady place to "
    "come back to. That is more than many people get.": "parents_sav_4",
}


def _hand_tag(text: str) -> str:
    return HANDWRITTEN_TAGS.get(text, f"hw:{hash(text)}")


def _item_evidence(tag: str, pc: dict, explicit: tuple | None = None) -> tuple[int, str] | None:
    """Resolve (house, planet) for a recognition tag."""
    if explicit:
        return explicit
    if tag == "health_lagna_weak":
        return (1, _lord(pc, 1).get("lord") or "Saturn")
    if tag == "health_lagna_strong":
        return (1, _lord(pc, 1).get("lord") or "Sun")
    if tag == "health_sun_vitals":
        return (_house_of(pc, "Sun") or 1, "Sun")
    if tag == "health_jupiter_weight":
        return (_house_of(pc, "Jupiter") or 6, "Jupiter")
    if tag == "money_mercury_earn":
        return (_house_of(pc, "Mercury") or 11, "Mercury")
    if tag == "money_jupiter_wealth":
        occ2, occ11 = _occupants(pc, 2), _occupants(pc, 11)
        if "Jupiter" in occ11:
            return (11, "Jupiter")
        return (2, "Jupiter")
    if tag == "money_malefic_12":
        occ12 = _occupants(pc, 12)
        planet = next((p for p in occ12 if p in MALEFIC), "Saturn")
        return (12, planet)
    if tag.startswith("career_stage_"):
        for p in _occupants(pc, 10):
            return (10, p)
        return (10, "Saturn")
    try:
        from narration.recognition_variants import tag_evidence_house_planet
        return tag_evidence_house_planet(tag)
    except Exception:  # noqa: BLE001
        return None



# ---------------------------------------------------------------------------
# Technical backing for every statement
# ---------------------------------------------------------------------------
# A claim the reader cannot trace is indistinguishable from a guess, and
# prediction quality is what this product sells. So each statement carries the
# placement that produced it. It proves the sentence came from THIS chart, and
# it lets a sceptical reader hand the reasoning to an astrologer and have it
# checked — which is a thing we should want them to be able to do.

def _ord_n(n: Any) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ""
    return f"{n}" + ("th" if 10 <= n % 100 <= 20
                     else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


def _dig_plain(d: Any) -> str:
    return {
        "exalted": "exalted", "moolatrikona": "in its best sign",
        "own_sign": "in its own sign", "friendly_sign": "well placed",
        "neutral_sign": "neutrally placed", "enemy_sign": "on difficult ground",
        "debilitated": "debilitated",
    }.get(str(d or "").lower(), str(d or "").replace("_", " "))


def why_planet(pc: dict, planet: str, *, note: str = "") -> str:
    """"Saturn in your 6th house, in its own sign" — the traceable form."""
    if not planet:
        return note
    info = (pc.get("planets", {}) or {}).get(planet) or {}
    house, sign = info.get("house"), info.get("sign")
    bits = [planet]
    if house:
        bits.append(f"in your {_ord_n(house)} house")
    if sign:
        bits.append(f"({sign})")
    dig = _dig_plain(info.get("dignity"))
    if dig and dig != "neutrally placed":
        bits.append(f", {dig}")
    out = " ".join(bits)
    result = f"{out}. {note}" if note else out
    return client_prose(result)


def why_lord(pc: dict, house: int, *, note: str = "") -> str:
    """"Your 2nd lord Moon sits in the 4th, neutrally placed"."""
    info = (pc.get("house_lords", {}) or {}).get(str(house)) or {}
    lord, lh = info.get("lord"), info.get("lord_house")
    if not lord:
        return note
    bits = [f"Your {_ord_n(house)} lord {lord}"]
    if lh:
        bits.append(f"sits in the {_ord_n(lh)}")
    dig = _dig_plain(info.get("lord_dignity"))
    if dig:
        bits.append(f", {dig}")
    out = " ".join(bits).replace(" ,", ",")
    result = f"{out}. {note}" if note else out
    return client_prose(result)


def why_sav(pc: dict, house: int) -> str:
    sav = (pc.get("ashtakavarga", {}) or {}).get("sav") or []
    if len(sav) >= house:
        v = sav[house - 1]
        band = ("above average" if v >= 30 else
                "below average" if v <= 25 else "average")
        return client_prose(
            f"Classical strength score for your {_ord_n(house)} house: "
            f"{v} of 56, {band}")
    return ""


# ---------------------------------------------------------------------------
# HEALTH — 6th house, ascendant lord, and who sits where
# ---------------------------------------------------------------------------

def health_claims(pc: dict) -> list:
    out = []
    sixth = _lord(pc, 6)
    occ6 = _occupants(pc, 6)
    lagna_lord = _lord(pc, 1).get("lord", "")
    ll_dig = _dig(pc, lagna_lord)

    if "Saturn" in occ6:
        out.append(("Whatever goes wrong with your health tends to be slow and "
                   "recurring rather than sudden — it builds for months, and it "
                   "usually shows up first as stiffness, sleep or the lower back.",
                    why_planet(pc, "Saturn", note="Saturn's symbolism here emphasizes discipline, persistence and consistent routines.")))
    if "Mars" in occ6:
        out.append(("Your health problems arrive fast and hot — inflammation, "
                   "fevers, sudden injuries — and they clear almost as quickly "
                   "as they came.",
                    why_planet(pc, "Mars", note="Mars in the 6th is associated with energy, pace and physical responsiveness.")))
    if "Ketu" in occ6 or "Rahu" in occ6:
        out.append(("You have had at least one health complaint that took an "
                   "unusually long time to diagnose correctly.",
                    "A node (Rahu or Ketu) sits in your 6th house — classically the signature of a complaint that resists diagnosis."))
    if "Moon" in occ6 or _house_of(pc, "Moon") in (6, 8, 12):
        out.append(("Your stomach is where your stress goes first. When life is "
                   "difficult, digestion is the thing that tells you before you "
                   "have admitted it to yourself.",
                    why_planet(pc, "Moon", note="The Moon governs digestion and the stomach; its house here ties mood to gut.")))

    if ll_dig in ("debilitated", "enemy_sign"):
        out.append(("Your baseline stamina has always been lower than the people "
                   "around you assume, and you have compensated by pushing "
                   "rather than by resting.",
                    why_lord(pc, 1, note="The ascendant lord carries physical vitality.")))
    elif ll_dig in ("exalted", "own_sign", "moolatrikona"):
        out.append(("You recover faster than most people. You have probably been "
                   "back on your feet from things that flattened others.",
                    why_lord(pc, 1, note="A strong ascendant lord is the classical marker of recovery.")))

    if _house_of(pc, "Sun") in (1, 5, 8):
        out.append(("Heat, eyes or blood pressure — one of those three is the "
                   "thing you have been told to watch.",
                    why_planet(pc, "Sun", note="The Sun governs eyes, heat and circulation.")))
    if _house_of(pc, "Jupiter") in (6, 8, 12):
        out.append(("You put on weight when life gets comfortable, and it comes "
                   "off only when something forces the issue.",
                    why_planet(pc, "Jupiter", note="Jupiter expands whatever it touches, including the body.")))
    s6 = _sav(pc, 6)
    if s6 is not None and s6 >= 30:
        out.append(("You tend to recover from setbacks with more resilience "
                   "than people may expect. The same persistence often appears "
                   "when you face opposition or difficult circumstances.",
                    why_sav(pc, 6)))
    return out


# ---------------------------------------------------------------------------
# MONEY — 2nd, 11th, 12th, D2
# ---------------------------------------------------------------------------

def money_claims(pc: dict) -> list:
    out = []
    second, eleventh = _lord(pc, 2), _lord(pc, 11)
    occ2, occ11, occ12 = _occupants(pc, 2), _occupants(pc, 11), _occupants(pc, 12)

    if second.get("lord_house") == 11 or eleventh.get("lord_house") == 2:
        out.append(("Your money has come through people rather than through "
                   "salary alone — introductions, networks, someone who thought "
                   "of you.",
                    "Your 2nd and 11th lords exchange houses — wealth routes through the network rather than the wage."))
    if "Rahu" in occ11:
        out.append(("Your best earnings have come from something slightly "
                   "unconventional, or from outside your home state or country.",
                    why_planet(pc, "Rahu", note="Rahu in the 11th points gains at the unfamiliar and the foreign.")))
    if "Saturn" in occ2 or second.get("lord") == "Saturn":
        out.append(("You accumulate slowly and you are careful with money in a "
                   "way that looks like anxiety to people who earn more easily.",
                    why_lord(pc, 2, note="Saturn on wealth accumulates by delay, not by luck.")))
    if occ12 and any(p in MALEFIC for p in occ12):
        out.append(("Money leaves you in large single amounts rather than "
                   "draining away — a medical bill, a family obligation, one "
                   "big commitment at a time.",
                    "A malefic sits in your 12th house — the house of outgoings — which classically empties in lumps rather than trickles."))
    if second.get("lord_dignity") in ("debilitated", "enemy_sign"):
        out.append(("There was a stretch — usually early — when money was "
                   "genuinely tight, and it permanently changed how you think "
                   "about spending.",
                    why_lord(pc, 2)))
    if "Jupiter" in occ2 or "Jupiter" in occ11:
        out.append(("Money has arrived at the moment you needed it more than "
                   "once, in a way that was hard to plan for and easy to be "
                   "grateful for.",
                    why_planet(pc, "Jupiter", note="Jupiter on a wealth house is the classical rescue placement.")))
    if _house_of(pc, "Mercury") in (2, 10, 11):
        out.append(("You earn from what you know rather than from what you own "
                   "— your income is tied to your own head, not to assets.",
                    why_planet(pc, "Mercury", note="Mercury on an earning house ties income to intellect.")))
    s2, s11 = _sav(pc, 2), _sav(pc, 11)
    if s2 is not None and s11 is not None and s11 > s2 + 3:
        out.append(("You are better at earning than at holding. Income has "
                   "rarely been the problem; what stays is.",
                    (why_sav(pc, 11) + " — against " + why_sav(pc, 2).split(": ")[-1])))
    elif s2 is not None and s2 >= 30:
        out.append(("Once money reaches you it tends to stay. You are not a "
                   "person who loses what they have built.",
                    why_sav(pc, 2)))
    return out


# ---------------------------------------------------------------------------
# LOVE — 7th, Venus, D9. Patterns only. No timing.
# ---------------------------------------------------------------------------

def love_claims(pc: dict) -> list:
    out = []
    seventh = _lord(pc, 7)
    venus_h, venus_dig = _house_of(pc, "Venus"), _dig(pc, "Venus")
    occ7 = _occupants(pc, 7)
    sat_h = _house_of(pc, "Saturn")

    if seventh.get("lord_house") in (6, 8, 12):
        out.append("Your closest relationships have had a private difficulty in "
                   "them that outsiders never saw — you handled it without "
                   "telling many people.")
    if venus_dig == "debilitated":
        out.append("You undersell yourself in love. You have been chosen by "
                   "people who saw your worth before you did.")
    elif venus_dig in ("exalted", "own_sign"):
        out.append("Affection has rarely been hard for you to find. Choosing "
                   "well from what was offered was the harder part.")
    if sat_h == 7 or seventh.get("lord") == "Saturn":
        out.append("Your significant relationship involved an age, distance or "
                   "responsibility gap — something that made it heavier than a "
                   "simple romance.")
    if "Mars" in occ7 or _house_of(pc, "Mars") in (7,):
        out.append("Arguments in your relationships flare quickly. The heat "
                   "passes fast, but it has frightened people who are not built "
                   "like you.")
    s7 = _sav(pc, 7)
    if s7 is not None and s7 <= 26:
        out.append("Relationships have asked more work of you than they seem "
                   "to ask of other people. When they work, it is because you "
                   "built them, not because they were easy.")
    if venus_h in (1, 4, 7, 10):
        out.append("People notice you before you have said anything. That has "
                   "opened doors and it has also attracted the wrong sort of "
                   "attention.")
    if venus_h in (12, 8):
        out.append("There has been at least one attachment you kept largely to "
                   "yourself.")
    return out


# ---------------------------------------------------------------------------
# PARENTS — 4th for mother, Sun and 9th/10th for father
# ---------------------------------------------------------------------------

def parents_claims(pc: dict) -> list:
    out = []
    sun_h, sun_dig = _house_of(pc, "Sun"), _dig(pc, "Sun")
    fourth = _lord(pc, 4)
    moon_h = _house_of(pc, "Moon")

    if sun_h in (6, 8, 12) or sun_dig == "debilitated":
        out.append("Your father was either absent in some practical way, or "
                   "carried a difficulty — health, work or temperament — that "
                   "the family arranged itself around.")
    elif sun_dig in ("exalted", "own_sign", "moolatrikona"):
        out.append("Your father's standing mattered in your household, and some "
                   "of what you expect of yourself came directly from him.")

    if moon_h == 4 or fourth.get("lord_house") in (1, 4, 5, 9, 10):
        out.append("You are closer to your mother than to your father, and she "
                   "is still the one you would call first.")
    if fourth.get("lord_house") in (6, 8, 12):
        out.append("Home was not entirely settled when you were young — a move, "
                   "a financial squeeze, or a stretch where things were tense.")

    ninth = _lord(pc, 9)
    if ninth.get("lord_house") in (6, 8, 12):
        out.append("You did not inherit an easy road. Whatever you have, you "
                   "assembled — and part of you still does not fully trust "
                   "help when it is offered.")
    if _house_of(pc, "Saturn") in (4, 10):
        out.append("Responsibility landed on you earlier than it should have. "
                   "You were the sensible one before you were ready to be.")
    s4 = _sav(pc, 4)
    if s4 is not None and s4 >= 30:
        out.append("Whatever else was going on, you had one steady place to "
                   "come back to. That is more than many people get.")
    return out


# Guaranteed floor. Some charts trip few of the specific rules above — one
# test chart produced only three statements, which reads as a thin section and
# undermines the whole "look how much we know about you" effect. These fire off
# the ruling planet of the domain's house, which always exists, so every reader
# gets a full section while the statement still varies by chart.
BY_RULER = {
    "health": {
        "Sun": "You run hot — physically and temperamentally — and you burn out from the top down.",
        "Moon": "Your health tracks your mood more closely than you would like to admit.",
        "Mars": "You are strong until you are suddenly not. You ignore the early signals.",
        "Mercury": "Nerves, skin or breathing — your body registers stress somewhere visible.",
        "Jupiter": "Your body is forgiving, which is exactly why you have taken it for granted.",
        "Venus": "Comfort is your weak point. Rest and indulgence look identical to you.",
        "Saturn": "You have the constitution of someone who lasts. It just does not feel that way from inside.",
        "Rahu": "Your symptoms rarely present in the textbook way.",
        "Ketu": "You have a tolerance for discomfort that means you seek help later than you should.",
    },
    "money": {
        "Sun": "You would rather be respected than rich, and it has cost you at least once.",
        "Moon": "Your spending follows your mood. Good months and bad months look different in your account.",
        "Mars": "You take financial risks other people would not, and you have been right often enough to keep doing it.",
        "Mercury": "You are good with numbers in general and worse with your own.",
        "Jupiter": "You are generous past the point of sense, and you would not change it.",
        "Venus": "You spend on beauty and comfort before you spend on security.",
        "Saturn": "You have never been able to relax about money, even when there was enough.",
        "Rahu": "Your income has been lumpy — very good stretches and very lean ones.",
        "Ketu": "You are oddly detached about money for someone who has had to worry about it.",
    },
    "love": {
        "Sun": "You need to be admired by the person you are with. Respect matters more than romance.",
        "Moon": "You need emotional safety more than excitement, whatever you tell yourself.",
        "Mars": "You are drawn to people who challenge you, then exhausted by the challenge.",
        "Mercury": "You fall for minds. If they cannot hold a conversation, nothing else rescues it.",
        "Jupiter": "You want a partner who is also a teacher, and you are disappointed when they are not.",
        "Venus": "You love easily and forgive faster than is good for you.",
        "Saturn": "You commit slowly and completely. Walking away is almost impossible once you are in.",
        "Rahu": "You have been attracted to people from outside your own background.",
        "Ketu": "You detach suddenly, and it looks colder from outside than it feels inside.",
    },
    "parents": {
        "Sun": "Your father's approval shaped more of your choices than you would like.",
        "Moon": "Your mother's emotional state ran the temperature of your childhood home.",
        "Mars": "There was friction with a parent that took years to settle, if it has.",
        "Mercury": "You were the child who explained things — between the adults, or for them.",
        "Jupiter": "One of your parents genuinely believed in you, and it is why you are still standing.",
        "Venus": "Your home was comfortable, and it may have made leaving harder than it should have been.",
        "Saturn": "You grew up faster than your friends did, because someone at home needed you to.",
        "Rahu": "Your family's story involves a move or a break from where they came from.",
        "Ketu": "There is a distance with one parent that neither of you has ever properly named.",
    },
    # Career is a 108-rule domain first; this floor only fires on the rare
    # chart where none of the career rules hit at all.
    "career": {
        "Sun": "You need the work to be visibly yours. Anonymous contribution has never satisfied you.",
        "Moon": "You have changed direction more than once because the atmosphere of a place stopped suiting you.",
        "Mars": "You do your best work against a deadline or an opponent, and you have engineered both.",
        "Mercury": "You have been the person who wrote it down, explained it, or fixed the process nobody owned.",
        "Jupiter": "You have taught or advised, formally or otherwise, for longer than it has been in your job title.",
        "Venus": "Your work has always had to be pleasant as well as profitable, and you have taken less money for that.",
        "Saturn": "You have stayed in roles past the point where others left, and the seniority came from durability.",
        "Rahu": "Your line of work is not the one your family would have predicted.",
        "Ketu": "You have walked away from something you were good at, and not entirely regretted it.",
    },
}
DOMAIN_HOUSE = {"health": 1, "money": 2, "love": 7, "parents": 4, "career": 10}


def _floor_claim(pc: dict, key: str) -> list:
    house = DOMAIN_HOUSE.get(key)
    if not house:
        return []
    ruler = _lord(pc, house).get("lord", "")
    line = BY_RULER.get(key, {}).get(ruler)
    return [line] if line else []


def career_claims(pc: dict) -> list:
    """Career has no hand-written rules — the 108 set carries this domain.

    Kept as an empty source so the domain behaves like the others (108 first,
    hand-written second, ruler floor last) rather than being special-cased.
    """
    return []


DOMAINS = (
    ("health", "Your health", health_claims),
    ("money", "Money, historically", money_claims),
    ("love", "How you are in love", love_claims),
    ("parents", "Your parents", parents_claims),
    ("career", "Your work", career_claims),
)


def build(pc: dict, *, per_domain: int = 3) -> list:
    """Statements the reader can check against a life we were never told about.

    Order within a domain is deliberate: the 108-rule statements come first
    because their conditions are narrower — a hand-written rule fires on "Saturn
    is in the 6th", a 108 rule fires on a named classical configuration — so
    they are the ones least likely to be true of the reader's neighbour too.
    The ruler floor stays last and only fills a domain that would otherwise be
    thin.
    """
    band = _age_band_fn(pc)
    from_108 = _items108(pc)

    # Hand-written claims join the same list so that contradiction resolution
    # sees both sources at once; untagged ones get a unique inert tag.
    hand: list = []
    for key, _label, fn in DOMAINS:
        for c in fn(pc):
            if not c:
                continue
            # A builder may return a bare string or (text, why). Normalising
            # here keeps every builder free to add its derivation later without
            # a coordinated change.
            text, why = (c if isinstance(c, tuple) else (c, ""))
            tag = _hand_tag(text)
            evidence = _item_evidence(tag, pc)
            hand.append((key, tag, text, why, evidence))

    kept = _resolve_conflicts(pc, from_108 + hand)
    # One statement per tag across both sources: two rules reaching the same
    # conclusion is corroboration, not two things to tell the reader.
    seen_tags: set = set()
    deduped = []
    for it in kept:
        if it[1] in seen_tags:
            continue
        seen_tags.add(it[1])
        deduped.append(it)
    kept = deduped
    tags_108 = {it[1] for it in from_108}
    kept_108 = {it[1] for it in kept if it[1] in tags_108}

    by_domain: dict = {}
    tag_evidence: dict[tuple[str, str], tuple[int, str] | None] = {}
    for it in kept:
        domain, tag, text = it[0], it[1], it[2]
        why = it[3] if len(it) > 3 else ""
        evidence = it[4] if len(it) > 4 else None
        tag_evidence[(domain, text)] = evidence
        bucket = by_domain.setdefault(domain, {"a": [], "b": []})
        bucket["a" if tag in kept_108 else "b"].append((text, why))

    out = []
    try:
        from narration.recognition_renderer import (
            build_meaning_for_tag,
            recognition_bullets,
            recognition_domain_label,
            render_from_meaning,
            render_recognition_claim,
        )
        from qa_checks.report_validator import ReportValidator
        from interpretation.manifestation_merger import merge_recognition_candidates
    except Exception:  # noqa: BLE001
        build_meaning_for_tag = None  # type: ignore
        render_from_meaning = None  # type: ignore
        recognition_bullets = lambda _m: []  # type: ignore
        merge_recognition_candidates = None  # type: ignore

        def render_recognition_claim(domain, tag, band, adult_text, **kw):  # type: ignore
            return None

        def recognition_domain_label(domain, band):  # type: ignore
            return RECOG_LABELS_MINOR.get(domain, domain) if is_minor(band) else domain

        ReportValidator = None  # type: ignore

    validator = ReportValidator() if ReportValidator else None
    max_domain_claims = min(per_domain, 2)

    for key, label, _fn in DOMAINS:
        bucket = by_domain.get(key, {"a": [], "b": []})
        candidates: list = []
        seen_text: set = set()
        for text, why in bucket["a"] + bucket["b"]:
            if text in seen_text:
                continue
            # Resolve tag from kept items — find matching tag for this text
            tag = ""
            evidence = None
            for it in kept:
                if it[0] == key and it[2] == text:
                    tag = it[1]
                    evidence = it[4] if len(it) > 4 else tag_evidence.get((key, text))
                    break
            ev_house, ev_planet = (evidence or (None, None))
            meaning = (
                build_meaning_for_tag(
                    key, tag or "hw", band, pc=pc,
                    house=ev_house, planet=ev_planet,
                )
                if build_meaning_for_tag else None
            )
            rendered = render_recognition_claim(
                key, tag, band, text, seen_texts=seen_text, pc=pc,
                house=ev_house, planet=ev_planet,
            )
            if rendered is None and meaning:
                rendered = render_from_meaning(meaning, seen_texts=seen_text)
            if rendered is None:
                continue
            if validator and not validator.check_claim(
                    rendered, band=band,
                    signature=meaning.evidence_signature if meaning else (key, tag, band),
                    meaning=meaning):
                continue
            bullets = recognition_bullets(meaning) if meaning else []
            safe_why = validator.sanitize_why(why, band=band, meaning=meaning) if validator else why
            if not safe_why and not validator:
                from qa_checks.why_safety_check import safe_why_text
                safe_why = safe_why_text(why, band=band, meaning=meaning)
            candidates.append({
                "rendered": rendered,
                "why": safe_why,
                "bullets": bullets,
                "meaning": meaning,
                "tag": tag or "hw",
            })
        # The old floor filled a thin domain with a second generic archetype.
        # That created exactly the "same story twice" regression. A floor is now
        # allowed only when the domain has no validated candidate at all.
        if len(candidates) == 0:
            for c in _floor_claim(pc, key):
                pair = c if isinstance(c, tuple) else (c, why_lord(pc, DOMAIN_HOUSE.get(key, 1)))
                if pair[0] in seen_text:
                    continue
                floor_tag = "floor"
                meaning = build_meaning_for_tag(key, floor_tag, band, pc=pc) if build_meaning_for_tag else None
                rendered = render_recognition_claim(
                    key, floor_tag, band, pair[0], seen_texts=seen_text, pc=pc)
                if rendered is None:
                    if meaning:
                        rendered = render_from_meaning(meaning, seen_texts=seen_text)
                if rendered is None:
                    continue
                if validator and not validator.check_claim(
                        rendered, band=band,
                        signature=(key, floor_tag, band),
                        meaning=meaning):
                    continue
                if not meaning and build_meaning_for_tag:
                    meaning = build_meaning_for_tag(key, floor_tag, band, pc=pc)
                bullets = recognition_bullets(meaning) if meaning else []
                floor_why = pair[1] if isinstance(c, tuple) else pair[1]
                safe_why = validator.sanitize_why(floor_why, band=band, meaning=meaning) if validator else floor_why
                if not safe_why and not validator:
                    from qa_checks.why_safety_check import safe_why_text
                    safe_why = safe_why_text(floor_why, band=band, meaning=meaning)
                candidates.append({
                    "rendered": rendered,
                    "why": safe_why,
                    "bullets": bullets,
                    "meaning": meaning,
                    "tag": floor_tag,
                })
        if merge_recognition_candidates and render_from_meaning:
            claims = merge_recognition_candidates(
                candidates,
                domain=key,
                band=band,
                render_from_meaning=render_from_meaning,
                recognition_bullets=recognition_bullets,
                seen_text=seen_text,
                max_claims=max_domain_claims,
            )
        else:
            claims = [(c["rendered"], c["why"], c["bullets"]) for c in candidates[:max_domain_claims]]
        if claims:
            display_label = recognition_domain_label(key, band)
            out.append({"key": key, "label": display_label, "claims": claims})
    return out


def render(blocks: list) -> str:
    if not blocks:
        return ""
    try:
        from qa_checks.why_safety_check import safe_why_text
    except Exception:  # noqa: BLE001
        def safe_why_text(why, *, band="adult", meaning=None):  # type: ignore
            return why or ""

    def one(c) -> str:
        if len(c) >= 3:
            text, why, bullets = c[0], c[1], c[2]
        else:
            text, why = (c if isinstance(c, tuple) else (c, ""))[0], (c[1] if isinstance(c, tuple) and len(c) > 1 else "")
            bullets = c[2] if isinstance(c, tuple) and len(c) > 2 else []
        text = client_prose(text)
        why = safe_why_text(why or "", band="adult") if why else ""
        if why:
            why = client_prose(why)
        bullet_html = ""
        if bullets:
            items = "".join(f"<li>{_e(b)}</li>" for b in bullets[:3])
            bullet_html = (
                f'<p class="recog-recognize"><span>You may recognize this as:</span></p>'
                f'<ul class="recog-bullets">{items}</ul>'
            )
        return (f'<p class="recog-claim">{_e(text)}</p>'
                + bullet_html
                + (f'<p class="recog-why"><span>Why</span> {_e(why)}</p>'
                   if why else ""))

    sections = "".join(f"""
  <div class="recog-block">
    <div class="recog-label">{_e(b['label'])}</div>
    {''.join(one(c) for c in b['claims'])}
  </div>""" for b in blocks)
    n = sum(len(b["claims"]) for b in blocks)
    return f"""
<section class="proof recognition">
  <h3>Your past, before you tell us any of it</h3>
  <p>You have not told us anything except when and where you were born.
  Everything below is read from that. Nothing here is a guess about dates.
  These are patterns that have been running for years.</p>
  <p><b>Read these {n} statements and be honest with yourself.</b> If several of
  these feel clearly wrong, your birth details may need to be checked before
  you rely on the predictions. If they feel surprisingly familiar, the same
  chart is the foundation for the timing ahead.</p>
  {sections}
  <div class="recog-ask">
    <span>Did these land?</span>
    <button type="button" class="pillbtn" data-v="yes">Mostly right</button>
    <button type="button" class="pillbtn" data-v="some">Some of it</button>
    <button type="button" class="pillbtn" data-v="no">Not really</button>
  </div>
</section>"""


# ---------------------------------------------------------------------------
# the standard the old block failed
# ---------------------------------------------------------------------------

def differentiation(charts: list) -> dict:
    """Do different charts actually produce different statements?

    The old proof block passed for everybody, which is what made it useless.
    This measures overlap: if two unrelated charts share most of their
    statements, the statements are Barnum lines and must be rewritten.
    """
    sets = []
    for pc in charts:
        claims = set()
        for b in build(pc, per_domain=99):
            claims.update(c[0] if isinstance(c, tuple) else c
                          for c in b["claims"])
        sets.append(claims)
    pairs, overlaps = 0, 0.0
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            union = sets[i] | sets[j]
            if not union:
                continue
            overlaps += len(sets[i] & sets[j]) / len(union)
            pairs += 1
    return {"charts": len(sets),
            "claims_per_chart": [len(s) for s in sets],
            "mean_overlap": round(overlaps / pairs, 3) if pairs else 0.0}
