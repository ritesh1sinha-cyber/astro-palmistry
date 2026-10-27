"""Guardrail for every free-text question a customer can type.

Covers horary, "Ask your chart" and the report follow-up chat. Runs *before* a
job is queued, a daily slot is spent, or a model is called, and again inside the
handlers as a second line of defence.

Why this exists: a horary question of "Gbnnml" received a full, confident
reading. Nothing looked at what had been typed. A chart can only answer a real
question, and some things people type should never be answered with a reading at
all (crisis, abuse, sexual content, harm to others).

Deterministic on purpose: no model call, no cost, no way to talk it round, and
it behaves the same when the LLM layer is down. Matching is on the normalised
text, so "f*ck", "f u c k" and "fuuuck" are caught as well as "fuck".

Public API
    check_question(text, kind) -> Verdict | None    # None means "go ahead"
    ensure_question_ok(text, kind)                    # raises QuestionRejected
`kind` is "horary", "user_question" or "chat". Chat accepts short replies such as
"thanks" or "ok"; the two report kinds need a real question.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .errors import UserError


class QuestionRejected(UserError):
    """Raised with a customer-safe message. `code` says which rule fired."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Verdict:
    code: str
    message: str


# ---------------------------------------------------------------------------
# What we say. One short paragraph each; these surface in a toast / chat bubble.
# ---------------------------------------------------------------------------
MSG = {
    "self_harm": (
        "We are really sorry you are feeling this way. You matter, and you do not "
        "have to carry this alone. Please talk to someone right now: Tele-MANAS "
        "14416 (free, 24x7), KIRAN 1800-599-0019, or iCall 9152987821. If you are "
        "in immediate danger, call 112. Outside India, find a local helpline at "
        "findahelpline.com. A chart reading cannot help with this, but a real "
        "person can."),
    "harm_others": (
        "We cannot help with anything about harming another person. If you or "
        "someone else is in danger, please call 112."),
    "lifespan": (
        "We do not predict death or how long anyone will live; no honest reading "
        "can. Ask about something you can act on instead: health habits, work, "
        "money, relationships or timing."),
    "sexual": (
        "We cannot answer sexual or explicit questions. Please ask about your "
        "life, work, relationships, health or money."),
    "abusive": (
        "Please keep the question respectful and we will gladly look at your "
        "chart. Rephrase it and try again."),
    "foetal_sex": (
        "We do not predict the sex of an unborn or future child; selecting or "
        "determining a child's sex is prohibited in India. We can look at the "
        "timing of conception, childbirth and wellbeing instead."),
    "injection": (
        "We can only answer questions about your own chart. Please ask about "
        "your life, work, relationships, health or money."),
    "gibberish": (
        "We could not understand that as a question. Please ask it in a full "
        "sentence, for example: “Will I get the job I interviewed for?”"),
    "too_short": (
        "Please write your question in a sentence or two so the chart can speak "
        "to it, for example: “When will my marriage happen?”"),
}


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s",
                       "7": "t", "@": "a", "$": "s", "!": "i"})
_SPACED = re.compile(r"\b(?:[a-z]\s){3,}[a-z]\b")        # "f u c k"


def _normalise(text: str) -> str:
    t = (text or "").lower()
    # letters separated by spaces, dots or stars: "f u c k", "f.u.c.k", "f*ck"
    t = _SPACED.sub(lambda m: m.group(0).replace(" ", ""), t)
    t = re.sub(r"\b(?:[a-z][.\-]){3,}[a-z]\b", lambda m: re.sub(r"[.\-]", "", m.group(0)), t)
    t = re.sub(r"(?<=[a-z])[\*#_]+(?=[a-z])", "", t)         # f*ck -> fck, f**k -> fk
    t = t.translate(_LEET)
    t = re.sub(r"(.)\1{2,}", r"\1", t)                    # fuuuck -> fuck
    t = re.sub(r"\s+", " ", t)
    return t


def _rx(*alts: str) -> re.Pattern[str]:
    return re.compile(r"\b(?:" + "|".join(alts) + r")\b", re.I)


# ---------------------------------------------------------------------------
# Rules (checked in this order)
# ---------------------------------------------------------------------------
_SELF_HARM = re.compile(
    r"\b(?:"
    r"suicid\w*|kill(?:ing)? (?:my ?self|me)|end(?:ing)? (?:my|this) life|end it all|"
    r"take my own life|take my life|(?:want|wanna|going|planning|plan) to die|"
    r"want(?:ed)? to be dead|better off dead|i (?:wish|hope) i (?:was|were) dead|"
    r"don'?t want to (?:live|be alive|exist)|no (?:reason|point) (?:to|in) liv\w*|"
    r"hurt(?:ing)? my ?self|harm(?:ing)? my ?self|cut(?:ting)? my ?self|hang(?:ing)? my ?self|"
    r"jump (?:off|from) (?:a |the )?(?:bridge|building|roof|terrace)|"
    r"overdose|poison my ?self|"
    # Hinglish / Telugu in Latin script
    r"khud ?kushi|aatm ?hatya|atm ?hatya|aathma ?hathya|"
    r"mar(?:na| jana| jaana) chah\w*|jeena nahi chah\w*|jeene ka (?:mann|man) nahi|"
    r"zindagi khatam|jaan de (?:du|dun)|"
    r"chach?ipovali|chanipovali|chavalani undi|brathakal?ani (?:ledu|ledhu)"
    r")\b", re.I)

_HARM_OTHERS = re.compile(
    r"\b(?:kill|murder|poison|stab|shoot|rape|assassinat\w*|acid attack|beat up|"
    r"hurt|harm|destroy)\b[^.?!]{0,25}\b(?:him|her|them|someone|somebody|"
    r"people|my (?:husband|wife|boss|mother in law|mil|father in law|father|mother|brother|"
    r"sister|neighbou?r|ex|enemy|enemies|rival|partner|boyfriend|girlfriend))\b"
    r"|\bhow (?:to|do i|can i) (?:kill|murder|poison|rape|stab|harm|hurt)\b"
    r"|\b(?:black magic|jadu|jaadu|tona|totka|maaran|curse)\b[^.?!]{0,30}\b(?:kill|destroy|ruin|harm|hurt|die)\b",
    re.I)

_LIFESPAN = re.compile(
    r"\b(?:when|how|what age|which year|at what age)\b[^?.!]{0,20}\bwill\b\s+"
    r"(?:i|he|she|we|they|my \w+|our \w+)\s+(?:die|pass away|expire|be dead)\b"
    r"|\bwill (?:i|he|she|my \w+) (?:die|pass away)\b"
    r"|\bhow long (?:will|am i going to|shall) (?:i|he|she|my \w+) (?:live|survive)\b"
    r"|\b(?:date|age|year) of (?:my |his |her )?(?:death|dying)\b"
    r"|\b(?:maut|mrityu|mrutyu)\s+kab\b|\bkab (?:marunga|marungi|marega|maregi)\b",
    re.I)

_SEXUAL = _rx(
    r"porn\w*", r"nudes?", r"naked", r"boobs?", r"nipples?", r"dicks?", r"dickheads?", r"cock", r"pussy",
    r"vagina", r"penis", r"cum", r"orgasm\w*", r"masturbat\w*", r"blowjobs?", r"handjobs?",
    r"horny", r"erotic\w*", r"sexy", r"sexting", r"threesome", r"onlyfans", r"xxx",
    r"fetish\w*", r"bdsm", r"hookups?", r"one night stand",
    r"sleep with (?:me|her|him|my \w+)", r"kiss me", r"be my (?:girl|boy)friend",
    r"send (?:me )?(?:pics|photos|nudes)", r"sex(?:ual)?",
    r"chudai", r"chodna", r"lund", r"lauda", r"gaand", r"chut", r"bhosd\w*", r"dengu\w*", r"modda")
# Legitimate astrology wording that contains the stem "sex".
_SEX_OK = re.compile(r"\bsex(?:ual)? (?:life|compatibility)\b", re.I)

_ABUSIVE = _rx(
    r"fuck\w*", r"motherfuck\w*", r"bitch\w*", r"bastards?", r"assholes?", r"dickheads?",
    r"cunts?", r"whores?", r"sluts?", r"shit\w*", r"bullshit", r"piss off", r"retard\w*",
    r"nigg\w+", r"faggots?", r"fagots?", r"kikes?", r"pakis?", r"fck\w*", r"fk", r"sht", r"ahole", r"dck", r"fuk\w*", r"fuq", r"phuck", r"shyt", r"btch",
    r"madarchod\w*", r"maderchod\w*", r"behenchod\w*", r"bhenchod\w*", r"bsdk", r"bkl", r"mkc",
    r"chutiy\w*", r"gandu\w*", r"randi", r"randiya", r"randwa", r"harami\w*", r"kutta", r"kutti", r"kamina", r"kamine",
    r"jhatu", r"bhadwa\w*", r"lanja\w*", r"dengey", r"pooku", r"puku", r"sulli",
    r"idiots?", r"morons?", r"dumbass", r"scumbag",
    r"you(?:'re| are| r)? (?:an? )?(?:stupid|dumb|useless|fraud|liar|cheat)",
    r"stupid (?:app|astrologer|website|site|bot|ai)",
    r"(?:shut|fuck|screw) (?:up|off|you)")

_FOETAL_SEX = re.compile(
    r"\b(?:boy or (?:a )?girl|girl or (?:a )?boy|male or female)\b[^?.!]{0,30}\b(?:baby|child|kid|born|pregnan\w*)\b"
    r"|\b(?:baby|child)\b[^?.!]{0,20}\b(?:boy or (?:a )?girl|girl or (?:a )?boy)\b"
    r"|\b(?:gender|sex)\b[^?.!]{0,15}\b(?:of|for)\b[^?.!]{0,15}\b(?:baby|child|unborn|foetus|fetus|pregnan\w*)\b"
    r"|\b(?:pregnan\w*|expecting|foetus|fetus|unborn|womb)\b[^?.!]{0,40}\b(?:boy|girl|son|daughter|gender|sex)\b"
    r"|\b(?:will|shall|am i going to|gonna)\b[^?.!]{0,25}\b(?:have|get|deliver|give birth to|be blessed with|bear)\s+"
    r"(?:a |an |one )?(?:baby )?(?:boy|girl|son|daughter)\b(?![\s-]*(?:friend|in[\s-]?law))"
    r"|\b(?:ladka|ladki|beta|beti)\b[^?.!]{0,20}\b(?:hoga|hogi|paida)\b",
    re.I)

_INJECTION = re.compile(
    r"\b(?:ignore|disregard|forget|override)\b[^.?!]{0,25}\b(?:previous|above|prior|earlier|all|your|the)\b"
    r"[^.?!]{0,20}\b(?:instructions?|prompts?|rules?|guidelines?)\b"
    r"|\b(?:system|developer|hidden|initial) prompt\b|\breveal your (?:prompt|instructions)\b"
    r"|\bjailbreak\b|\bdeveloper mode\b|\bdan mode\b|\bpretend (?:to be|you are)\b",
    re.I)


# ---------------------------------------------------------------------------
# "Is this a real question" - gibberish and too-short input
# ---------------------------------------------------------------------------
_KEYBOARD = ("qwertyuiop", "asdfghjkl", "zxcvbnm", "poiuytrewq", "lkjhgfdsa", "mnbvcxz")
_ACRONYMS = {"tv", "pc", "dr", "mr", "mrs", "ms", "vs", "pls", "plz", "ctc", "sbi", "hdfc",
             "gst", "pf", "ppf", "cgpa", "hr", "ssc", "rbi", "cbse", "upsc", "mbbs", "lkg", "mnc",
             "nbfc", "sebi", "icici"}
_RARE_CONSONANT_WORDS = {"strength", "strengths", "length", "lengths", "angsts", "twelfths",
                         "sixths", "months", "rhythm", "rhythms"}
# One-word questions are fine when the word names what people actually ask about.
_TOPICS = {
    "marriage", "marry", "wedding", "love", "job", "jobs", "career", "work", "money", "wealth",
    "health", "house", "home", "property", "land", "travel", "abroad", "visa", "exam", "exams",
    "baby", "child", "children", "pregnancy", "business", "divorce", "court", "case", "loan",
    "promotion", "relationship", "salary", "study", "studies", "education", "luck", "fortune",
    "shaadi", "vivah", "naukri", "paisa", "kaam", "ghar", "videsh", "pariksha", "vyapar",
    "pelli", "udyogam", "dabbu", "illu", "arogyam"}


def _plausible(tok: str) -> bool:
    """A token that could be a word in some language we serve."""
    raw = tok
    w = tok.lower()
    if not w.isascii():                      # Devanagari, Telugu ... script: trust it
        return len(w) >= 2
    if len(w) == 1:
        return w in ("a", "i")
    if w in _ACRONYMS:
        return True
    if not re.search(r"[aeiouy]", w):
        return False
    if re.search(r"(.)\1{2,}", w):
        return False
    if len(w) >= 4 and any(w[i:i + 4] in k for k in _KEYBOARD for i in range(len(w) - 3)):
        return False
    if len(w) >= 6 and re.fullmatch(r"(.{2,3})\1+.?", w):
        return False
    if w in _RARE_CONSONANT_WORDS:
        return True
    if re.search(r"[^aeiouy]{5,}", w):
        return False
    if len(w) >= 7 and len(re.findall(r"[aeiouy]", w)) / len(w) < 0.2:
        return False
    return True


def _words(text: str) -> list[str]:
    return re.findall(r"[^\W\d_]+", text or "")


def _real_question(text: str, kind: str) -> Verdict | None:
    toks = _words(text)
    if not toks:
        return Verdict("gibberish", MSG["gibberish"])
    good = [t for t in toks if _plausible(t)]
    if len(good) / len(toks) < 0.6:
        return Verdict("gibberish", MSG["gibberish"])
    if kind == "chat":
        return None                          # "ok", "thanks" and the like are fine
    uniq = {t.lower() for t in good}
    if len(uniq) < 2 and not (uniq & _TOPICS):
        return Verdict("too_short", MSG["too_short"])
    return None


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------
def check_question(text: str, kind: str = "chat") -> Verdict | None:
    """Return a Verdict when the text must not be answered, else None."""
    raw = (text or "").strip()
    if not raw:
        return Verdict("too_short", MSG["too_short"])
    norm = _normalise(raw)
    low = raw.lower()

    for code, rx in (("self_harm", _SELF_HARM), ("harm_others", _HARM_OTHERS)):
        if rx.search(low) or rx.search(norm):
            return Verdict(code, MSG[code])
    if _LIFESPAN.search(low):
        return Verdict("lifespan", MSG["lifespan"])
    sexual_text = _SEX_OK.sub(" ", norm)
    if _SEXUAL.search(sexual_text):
        return Verdict("sexual", MSG["sexual"])
    if _ABUSIVE.search(norm):
        return Verdict("abusive", MSG["abusive"])
    if _FOETAL_SEX.search(low):
        return Verdict("foetal_sex", MSG["foetal_sex"])
    if _INJECTION.search(low):
        return Verdict("injection", MSG["injection"])
    return _real_question(raw, kind)


def ensure_question_ok(text: str, kind: str = "chat") -> None:
    v = check_question(text, kind)
    if v:
        raise QuestionRejected(v.code, v.message)
