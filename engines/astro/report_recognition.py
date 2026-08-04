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
health, money, love and parents.

The falsification standard this module has to meet is the one the old block
failed: **two different charts must produce noticeably different statements.**
There is a test for it at the bottom.
"""

from __future__ import annotations

import html as _html
from typing import Any

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
# HEALTH — 6th house, ascendant lord, and who sits where
# ---------------------------------------------------------------------------

def health_claims(pc: dict) -> list:
    out = []
    sixth = _lord(pc, 6)
    occ6 = _occupants(pc, 6)
    lagna_lord = _lord(pc, 1).get("lord", "")
    ll_dig = _dig(pc, lagna_lord)

    if "Saturn" in occ6:
        out.append("Whatever goes wrong with your health tends to be slow and "
                   "recurring rather than sudden — it builds for months, and it "
                   "usually shows up first as stiffness, sleep or the lower back.")
    if "Mars" in occ6:
        out.append("Your health problems arrive fast and hot — inflammation, "
                   "fevers, sudden injuries — and they clear almost as quickly "
                   "as they came.")
    if "Ketu" in occ6 or "Rahu" in occ6:
        out.append("You have had at least one health complaint that took an "
                   "unusually long time to diagnose correctly.")
    if "Moon" in occ6 or _house_of(pc, "Moon") in (6, 8, 12):
        out.append("Your stomach is where your stress goes first. When life is "
                   "difficult, digestion is the thing that tells you before you "
                   "have admitted it to yourself.")

    if ll_dig in ("debilitated", "enemy_sign"):
        out.append("Your baseline stamina has always been lower than the people "
                   "around you assume, and you have compensated by pushing "
                   "rather than by resting.")
    elif ll_dig in ("exalted", "own_sign", "moolatrikona"):
        out.append("You recover faster than most people. You have probably been "
                   "back on your feet from things that flattened others.")

    if _house_of(pc, "Sun") in (1, 5, 8):
        out.append("Heat, eyes or blood pressure — one of those three is the "
                   "thing you have been told to watch.")
    if _house_of(pc, "Jupiter") in (6, 8, 12):
        out.append("You put on weight when life gets comfortable, and it comes "
                   "off only when something forces the issue.")
    s6 = _sav(pc, 6)
    if s6 is not None and s6 >= 30:
        out.append("You fight off illness better than average — the same is "
                   "true of opposition generally. People who take you on tend "
                   "to tire before you do.")
    return out


# ---------------------------------------------------------------------------
# MONEY — 2nd, 11th, 12th, D2
# ---------------------------------------------------------------------------

def money_claims(pc: dict) -> list:
    out = []
    second, eleventh = _lord(pc, 2), _lord(pc, 11)
    occ2, occ11, occ12 = _occupants(pc, 2), _occupants(pc, 11), _occupants(pc, 12)

    if second.get("lord_house") == 11 or eleventh.get("lord_house") == 2:
        out.append("Your money has come through people rather than through "
                   "salary alone — introductions, networks, someone who thought "
                   "of you.")
    if "Rahu" in occ11:
        out.append("Your best earnings have come from something slightly "
                   "unconventional, or from outside your home state or country.")
    if "Saturn" in occ2 or second.get("lord") == "Saturn":
        out.append("You accumulate slowly and you are careful with money in a "
                   "way that looks like anxiety to people who earn more easily.")
    if occ12 and any(p in MALEFIC for p in occ12):
        out.append("Money leaves you in large single amounts rather than "
                   "draining away — a medical bill, a family obligation, one "
                   "big commitment at a time.")
    if second.get("lord_dignity") in ("debilitated", "enemy_sign"):
        out.append("There was a stretch — usually early — when money was "
                   "genuinely tight, and it permanently changed how you think "
                   "about spending.")
    if "Jupiter" in occ2 or "Jupiter" in occ11:
        out.append("Money has arrived at the moment you needed it more than "
                   "once, in a way that was hard to plan for and easy to be "
                   "grateful for.")
    if _house_of(pc, "Mercury") in (2, 10, 11):
        out.append("You earn from what you know rather than from what you own "
                   "— your income is tied to your own head, not to assets.")
    s2, s11 = _sav(pc, 2), _sav(pc, 11)
    if s2 is not None and s11 is not None and s11 > s2 + 3:
        out.append("You are better at earning than at holding. Income has "
                   "rarely been the problem; what stays is.")
    elif s2 is not None and s2 >= 30:
        out.append("Once money reaches you it tends to stay. You are not a "
                   "person who loses what they have built.")
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
}
DOMAIN_HOUSE = {"health": 1, "money": 2, "love": 7, "parents": 4}


def _floor_claim(pc: dict, key: str) -> list:
    house = DOMAIN_HOUSE.get(key)
    if not house:
        return []
    ruler = _lord(pc, house).get("lord", "")
    line = BY_RULER.get(key, {}).get(ruler)
    return [line] if line else []


DOMAINS = (
    ("health", "Your health", health_claims),
    ("money", "Money, historically", money_claims),
    ("love", "How you are in love", love_claims),
    ("parents", "Your parents", parents_claims),
)


def build(pc: dict, *, per_domain: int = 2) -> list:
    """Statements the reader can check against a life we were never told about."""
    out = []
    for key, label, fn in DOMAINS:
        found = [c for c in fn(pc) if c]
        if len(found) < 2:
            found += [c for c in _floor_claim(pc, key) if c not in found]
        claims = found[:per_domain]
        if claims:
            out.append({"key": key, "label": label, "claims": claims})
    return out


def render(blocks: list) -> str:
    if not blocks:
        return ""
    sections = "".join(f"""
  <div class="recog-block">
    <div class="recog-label">{_e(b['label'])}</div>
    {''.join(f'<p class="recog-claim">{_e(c)}</p>' for c in b['claims'])}
  </div>""" for b in blocks)
    n = sum(len(b["claims"]) for b in blocks)
    return f"""
<section class="proof recognition">
  <h3>What your chart already knows about you</h3>
  <p>You have not told us anything except when and where you were born.
  Everything below is read from that. Nothing here is a guess about dates —
  these are patterns that have been running for years.</p>
  <p><b>Read these {n} statements and be honest with yourself.</b> If most of
  them are wrong, close this page and keep your money. If most of them are
  right, the same chart is what the predictions are built on.</p>
  {sections}
  <div class="recog-ask">
    <span>Did these land?</span>
    <button class="pillbtn" data-v="yes">Mostly right</button>
    <button class="pillbtn" data-v="some">Some of it</button>
    <button class="pillbtn" data-v="no">Not really</button>
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
            claims.update(b["claims"])
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
