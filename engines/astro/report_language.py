#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared client-facing language normalizers for all report lanes."""
from __future__ import annotations

import re


def neutralize_spouse_terms(line: str) -> str:
    """Partner references use spouse / partner - not wife / husband."""
    if not line:
        return ""
    for pat, repl in (
        (r"\bthe husband and wife\b", "you and your spouse"),
        (r"\bHusband and Wife\b", "Spouse"),
        (r"\bhusband and wife\b", "spouse and partner"),
        (r"\bBrother/Husband\b", "Brother/partner"),
        (r"\bYour spouse and wife\b", "You and your spouse"),
        (r"\bYour husband and wife\b", "You and your spouse"),
        (r"\bdefines the husband\b", "defines the spouse"),
        (r"\bdefines the wife\b", "defines the spouse"),
        (r"\bstrongest wife placement\b", "strongest spouse placement"),
        (r"\bstrongest husband placement\b", "strongest spouse placement"),
        (r"\bMarriage and your wife\b", "Marriage and partner"),
        (r"\bMarriage and your husband\b", "Marriage and partner"),
        (r"\bWife's Characteristics\b", "Spouse characteristics"),
        (r"\bWife could\b", "Spouse could"),
        (r"\bwife could\b", "spouse could"),
        (r"\bHusband could\b", "Spouse could"),
        (r"\bhusband could\b", "spouse could"),
        (r"\bin Your wife\b", "in your spouse"),
        (r"\bin your wife\b", "in your spouse"),
        (r"\bin Your husband\b", "in your spouse"),
        (r"\bin your husband\b", "in your spouse"),
        (r"\bin the wife\b", "in the spouse"),
        (r"\bin the husband\b", "in the spouse"),
        (r"\bYour wife\b", "Your spouse"),
        (r"\bYour husband\b", "Your spouse"),
        (r"\byour wife\b", "your spouse"),
        (r"\byour husband\b", "your spouse"),
        (r"\bthe wife\b", "the spouse"),
        (r"\bthe husband\b", "the spouse"),
        (r"\bwife is\b", "spouse is"),
        (r"\bhusband is\b", "spouse is"),
        (r"\bon her body\b", "on their body"),
        (r"\bon his body\b", "on their body"),
        (r"\bfrom her past life\b", "from their past life"),
        (r"\bfrom his past life\b", "from their past life"),
    ):
        line = re.sub(pat, repl, line, flags=re.I)
    return line


def neutralize_partner_pronouns(line: str) -> str:
    """Gender-neutral they/their when prose clearly describes the partner."""
    if not line or not re.search(r"\b(spouse|partner|marriage|7th|wife|husband)\b", line, re.I):
        return line
    subs = (
        (r"\bShe is practical\b", "They are practical"),
        (r"\bshe is practical\b", "they are practical"),
        (r"\bShe may\b", "They may"),
        (r"\bshe may\b", "they may"),
        (r"\bShe is\b", "They are"),
        (r"\bshe holds themselves\b", "they hold themselves"),
        (r"\bshe holds herself\b", "they hold themselves"),
        (r"\bHe is\b", "They are"),
        (r"\bhe holds himself\b", "they hold themselves"),
    )
    for pat, repl in subs:
        line = re.sub(pat, repl, line)
    return line


def normalize_sentence_dashes(text: str) -> str:
    """Replace sentence-joining em dashes with full stops; keep mid-phrase dashes."""
    if not text:
        return ""
    # Only convert when the following word starts a new sentence (capital letter).
    out = re.sub(r"\s+—\s+(?=[A-Z])", ". ", text)
    out = re.sub(r"\.\s+\.", ".", out)
    out = re.sub(r"\.{2,}", ".", out)
    return out.strip()


def client_prose(line: str) -> str:
    """Full client-text pass for scraped or composed prediction lines."""
    line = neutralize_spouse_terms(line)
    line = neutralize_partner_pronouns(line)
    line = fix_house_ordinals(line)
    line = normalize_sentence_dashes(line)
    return line


def fix_house_ordinals(text: str) -> str:
    """Fix invalid ordinals such as 1th/2th/3th without touching correct forms."""
    if not text:
        return ""
    out = text
    for bad, good in (
        (r"\b1th\b", "1st"),
        (r"\b2th\b", "2nd"),
        (r"\b3th\b", "3rd"),
        (r"\b21th\b", "21st"),
        (r"\b22th\b", "22nd"),
        (r"\b23th\b", "23rd"),
        (r"\b31th\b", "31st"),
    ):
        out = re.sub(bad, good, out)
    return out


def house_ordinal(n) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ""
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


_CLAIM_TECH = re.compile(
    r"(career chart|home chart|wealth chart|marriage chart|children chart|"
    r"health chart|learning chart|spiritual chart|divisional chart|"
    r"\bD(?:1|2|3|4|7|9|10|12|16|20|24|27|30|40|45|60)\b|"
    r"karakamsa|functional lord|dispositor|lunar timing|\bnadi\b|"
    r"\bconfluence\b|\bantardasha\b|"
    r"\b\d+(?:st|nd|rd|th)\s+house\b)",
    re.I,
)


def strip_visible_claim_jargon(text: str) -> str:
    """Keep main customer claims human; drop engine-jargon sentences."""
    if not text:
        return ""
    text = fix_house_ordinals(text)
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    kept = [p for p in parts if p and not _CLAIM_TECH.search(p)]
    if kept:
        return normalize_sentence_dashes(" ".join(kept).strip())
    # Fallback: first sentence only if everything looked technical.
    return normalize_sentence_dashes(parts[0].strip() if parts else "")


HUMAN_PHRASES: tuple[tuple[str, str], ...] = (
    ("under strain", "needs more care right now"),
    ("favourable", "looks supportive"),
    ("mixed chapter", "mixed phase. Some things move, some need patience"),
    ("supportive way", "a more supportive phase"),
    ("demanding stretch", "a period that asks more from you"),
    ("protect energy", "protect your energy"),
    ("more pressure than payoff", "more effort than immediate reward"),
    ("house strength", "support from this part of the chart"),
    ("the birth chart gives a mixed picture", "this area looks mixed for you"),
    ("birth chart gives a mixed picture", "this area looks mixed for you"),
    ("broadly supportive", "there is some support, but it is not completely smooth"),
    ("planetary pressure", "this area may require more patience and attention"),
    ("transit is favourable", "this is a more supportive period"),
    ("transit is unfavourable", "this period needs more caution"),
    ("lunar cycle", "your secondary timing system"),
    ("chart promise", "your birth chart supports this pattern"),
    ("confluence", "several parts of your chart point in the same direction"),
)

SENTENCE_REWRITES: tuple[tuple[str, str], ...] = (
    (r"\bThis window stays open and supportive\.",
     "This is a period you can use more actively."),
    (r"\bMixed signals\.?\s*Patience over big moves\.?",
     ""),
    (r"\bPatience over big moves\.?",
     ""),
    (r"\bSome things move while others need patience\. Avoid forcing the result\.?",
     ""),
    (r"\bProgress may feel slower\. Focus on consistency rather than forcing a result\.?",
     ""),
    (r"\bactivates your (\d+)(?:st|nd|rd|th)? house\b",
     "puts more focus on that part of life"),
    (r"\bYour chart shows\b", "What stands out now is"),
    (r"\byour chart shows\b", "what stands out now is"),
    (r"\bmay experience\b", "may show up as"),
    (r"\bnative\b", "you"),
    (r"\bbroadly\b", ""),
)


def humanise_client_language(text: str) -> str:
    """Light-touch client wording pass. It changes labels, not astrology facts."""
    if not text:
        return ""
    out = fix_house_ordinals(text)
    for old, new in HUMAN_PHRASES:
        out = re.sub(r"\b" + re.escape(old) + r"\b", new, out, flags=re.I)
    for pat, repl in SENTENCE_REWRITES:
        out = re.sub(pat, repl, out, flags=re.I)
    out = re.sub(r"\s{2,}", " ", out)
    return normalize_sentence_dashes(out.strip())


PLANET_INFLUENCE = {
    "Sun": "Visibility, authority and recognition carry more weight in this stretch.",
    "Moon": "Mood, home rhythm and people close to you shape more of the day-to-day.",
    "Mars": "Drive rises — and so does the chance of friction if you push too hard.",
    "Mercury": "Talks, paperwork and clear wording matter more than usual.",
    "Jupiter": "Growth, support, guidance and opportunities to expand.",
    "Venus": "Goodwill, comfort and relationship ease are easier to access.",
    "Saturn": "Patience, responsibility and slower but more durable progress.",
    "Rahu": "New directions, ambition and unfamiliar opportunities. Verify what looks too convenient.",
    "Ketu": "Attachment loosens here. Gripping harder rarely helps.",
}

TRAJECTORY_EXPLAIN = {
    # Fallback only — prefer AREA_TRAJECTORY_VARIANTS.
    "up": "Progress is easier when you act deliberately.",
    "mixed": "Some things move while others need patience.",
    "down": "Progress may feel slower than expected.",
}

# Multiple distinct lines per area × direction so successive windows do not
# reuse one template sentence (Final Targeted Modifications §1–6).
AREA_TRAJECTORY_VARIANTS: dict[str, dict[str, list[str]]] = {
    "career": {
        "up": [
            "Your work can become easier to notice during this phase. Use the opening to take ownership of work that has visible impact.",
            "This is a better period to ask for responsibility, recognition or a role that reflects the work you have already been doing.",
            "Recognition is easier when you keep your work visible and document results others can see.",
        ],
        "mixed": [
            "Your work is stronger than the recognition you are receiving right now. Steady visibility matters more than sudden changes.",
            "Progress is possible, but it is more likely through consistent ownership than one dramatic breakthrough.",
            "Keep delivering work that can be clearly demonstrated. Visibility still matters more than rushing a career change.",
        ],
        "down": [
            "Recognition may take longer than expected. Focus on building visible, repeatable results rather than forcing a quick change.",
            "This is a period to strengthen your position rather than make a rushed career decision.",
            "Effort counts, but progress may feel slow. Protect your reputation and finish what you start.",
        ],
    },
    "money": {
        "up": [
            "This is a better stretch for strengthening savings and practical cash-flow decisions.",
            "Use this phase to improve income rhythm and put money decisions on firmer ground.",
            "Gains are more likely when you act on practical plans rather than speculative shortcuts.",
        ],
        "mixed": [
            "Income can remain manageable, but larger gains are more likely through disciplined decisions than quick opportunities.",
            "Keep commitments manageable and avoid stretching your budget simply because an opportunity looks attractive.",
            "There may be openings to improve finances, but they work best with careful judgment and a clear budget.",
        ],
        "down": [
            "Use this phase to protect cash flow. Review recurring expenses and keep a buffer for costs that are difficult to predict.",
            "Avoid unnecessary financial commitments and give yourself more room for unexpected expenses.",
            "Protect what you already have. Delay non-essential spending until the picture is clearer.",
        ],
    },
    "love": {
        "up": [
            "Connection and goodwill are easier to rebuild when conversations stay clear.",
            "Warmth returns more easily when both people feel heard.",
            "This phase favours honest appreciation and practical support between partners.",
        ],
        "mixed": [
            "Communication matters more than intensity during this phase. Small misunderstandings can become larger if left unresolved.",
            "Expectations and timing may need more patience. Avoid turning a temporary frustration into a permanent decision.",
            "This phase favours practical conversations and giving both people enough space to respond before drawing conclusions.",
        ],
        "down": [
            "Small misunderstandings can carry more weight than usual. Clear communication matters.",
            "Protect the bond from unnecessary escalation; clarity matters more than winning an argument.",
            "Give difficult conversations enough time. Pushing for an instant answer can make things harder.",
        ],
    },
    "home": {
        "up": [
            "Home and family matters settle more easily when handled calmly.",
            "Practical household conversations are more likely to produce agreement now.",
            "A calmer home rhythm is easier to restore with patient discussion.",
        ],
        "mixed": [
            "Home is mostly workable, but one recurring responsibility may still pull attention.",
            "Family discussions may need extra patience. Give everyone enough time to respond before making a final decision.",
            "Keep important home conversations practical. Rushing a settlement often creates another round of discussion.",
        ],
        "down": [
            "Family discussions may need extra patience. Give everyone enough time to respond before making a final decision.",
            "Household or living arrangements may require another round of checking. Avoid rushing simply because you want the matter finished.",
            "Give family matters time to settle. Calm follow-through helps more than forcing a quick close.",
        ],
    },
    "children": {
        "up": [
            "Progress with children or creative work is easier when support is consistent.",
            "Encouragement and steady attention help progress show more clearly.",
            "Creative or child-related efforts respond well to patient guidance.",
        ],
        "mixed": [
            "Progress around children or creative work is real but uneven — patience helps more than pressure.",
            "Keep expectations realistic. Consistent attention helps more than pushing for an immediate result.",
            "There can be genuine movement here, but timing may not be neat. Stay present without forcing the pace.",
        ],
        "down": [
            "Progress may require repetition, but the effort can become useful later.",
            "Keep supporting step by step. Pressure rarely accelerates the outcome here.",
            "Focus on patience and practical help rather than expecting a quick breakthrough.",
        ],
    },
    "health": {
        "up": [
            "This is a better period for rebuilding routines and addressing habits you have been postponing.",
            "Steady routines make it easier to maintain energy and wellbeing.",
            "A supportive stretch for sleep, movement and preventive care.",
        ],
        "mixed": [
            "Use this phase to strengthen sleep, food, movement and other daily routines. Consistency matters more than trying to change everything at once.",
            "Focus on sleep, consistency and preventive care. Progress is easier when you avoid pushing for instant results.",
            "Small daily habits matter more than dramatic resets. Keep the basics steady.",
        ],
        "down": [
            "Keep routines steady and avoid neglecting small issues that can become bigger when ignored.",
            "Protect rest and do not ignore small lifestyle signals.",
            "This is a time to simplify and recover rhythm rather than adding pressure to your schedule.",
        ],
    },
    "learning": {
        "up": [
            "Understanding can come more naturally during this period. Use it to finish something that previously felt difficult or incomplete.",
            "Study, guidance and skill-building move more easily with structured effort.",
            "A good stretch for finishing courses, exams or long-pending learning goals.",
        ],
        "mixed": [
            "This phase rewards structured learning. Revisiting difficult material or working with a good mentor can produce better results than trying to move quickly.",
            "Learning is available, but progress may come through repetition, structure and guidance rather than quick understanding.",
            "A good teacher or clearer plan can make this period much more productive.",
        ],
        "down": [
            "Progress may require repetition, but the effort can become useful later.",
            "Simplify the plan and rebuild momentum through review rather than rushing ahead.",
            "Do not measure yourself only by speed. Steady revision often beats forcing breakthroughs.",
        ],
    },
    "inner": {
        "up": [
            "Clarity about priorities comes more readily when you leave space for quiet reflection.",
            "Quiet time can help you see what still deserves your energy.",
            "Inner clarity improves when you reduce noise and keep a simple routine.",
        ],
        "mixed": [
            "You may feel pulled between commitments and the need for personal space.",
            "You may need more personal space while deciding what deserves your energy.",
            "Priorities can feel less fixed. Give yourself room to rethink without forcing a conclusion.",
        ],
        "down": [
            "You may feel more inward or restless than usual. Give yourself space instead of forcing clarity.",
            "Give yourself room to step back before major personal decisions.",
            "Withdrawal can be protective here. Rest before committing to another demand.",
        ],
    },
}

# Backward-compatible first-choice map.
AREA_TRAJECTORY: dict[str, dict[str, str]] = {
    area: {d: variants[0] for d, variants in dirs.items() if variants}
    for area, dirs in AREA_TRAJECTORY_VARIANTS.items()
}

AREA_EXPECT: dict[str, dict[str, str]] = {
    "career": {
        "up": "Progress is likely when you keep ownership visible and consistent.",
        "mixed": "Progress is likely, but it may come through steady visibility rather than one sudden breakthrough.",
        "down": "This is a period to strengthen your position rather than make a rushed career change.",
    },
    "money": {
        "up": "There is room to strengthen finances through practical, disciplined choices.",
        "mixed": "There are opportunities to improve finances, but avoid taking unnecessary risks simply because an opportunity looks attractive.",
        "down": "Protect cash flow and delay non-essential financial risks.",
    },
    "love": {
        "up": "Connection improves when goodwill and clear talk stay in the foreground.",
        "mixed": "The relationship moves best when communication stays calm and practical.",
        "down": "Protect the bond from unnecessary escalation; clarity matters more than winning.",
    },
    "home": {
        "up": "The situation becomes easier when communication stays calm and practical.",
        "mixed": "Home settles faster when one recurring responsibility is handled without rushing a big decision.",
        "down": "Give family or property matters time to settle rather than forcing a conclusion.",
    },
    "children": {
        "up": "Children or creative projects respond well to steady encouragement.",
        "mixed": "Progress is uneven — consistent attention helps more than pressure.",
        "down": "Keep expectations realistic and support progress step by step.",
    },
    "health": {
        "up": "Steady routines make it easier to maintain energy and wellbeing.",
        "mixed": "A good period to focus on sleep, consistency and preventive care.",
        "down": "Protect rest and do not ignore small lifestyle signals.",
    },
    "learning": {
        "up": "Guidance and structured study make progress more likely.",
        "mixed": "A good teacher or mentor can make this period much more productive.",
        "down": "Simplify the plan and rebuild momentum through repetition.",
    },
    "inner": {
        "up": "Quiet reflection helps priorities come into clearer focus.",
        "mixed": "You may need more personal space while deciding what deserves your energy.",
        "down": "Give yourself room to step back before major personal decisions.",
    },
}

CHAPTER_AREA_LINE: dict[str, dict[str, str]] = {
    "career": {
        "child": "This chapter emphasizes consistent study, guidance and visible progress.",
        "teen": "This chapter emphasizes consistent study, guidance and visible progress.",
        "young_adult": "This chapter emphasizes education, skills and early professional responsibility.",
        "adult": "This chapter emphasizes responsibility, visibility and long-term professional progress.",
        "mature_adult": "This chapter emphasizes leadership, visibility and sustained professional responsibility.",
        "senior": "This chapter emphasizes influence, mentoring and the value of experience.",
    },
    "money": {
        "child": "This chapter emphasizes careful resource habits and family resource awareness.",
        "teen": "This chapter emphasizes careful resource management and practical money habits.",
        "young_adult": "This chapter emphasizes building financial independence and careful resource decisions.",
        "adult": "This chapter can increase financial opportunities, but careful judgment around gains and spending matters.",
        "mature_adult": "This chapter can increase financial opportunities, but careful judgment around gains and spending matters.",
        "senior": "This chapter emphasizes preservation, family resources and careful financial management.",
    },
    "love": {
        "child": "This chapter emphasizes friendships, communication and close bonds.",
        "teen": "This chapter emphasizes friendships, communication and close bonds.",
        "young_adult": "This chapter can make expectations and communication more important in relationships.",
        "adult": "This chapter can make expectations and communication more important.",
        "mature_adult": "This chapter can make expectations and communication more important.",
        "senior": "This chapter emphasizes companionship, family bonds and steady communication.",
    },
    "home": {
        "adult": "This chapter keeps family responsibilities active even when the home situation itself is relatively stable.",
    },
    "children": {
        "adult": "This chapter can raise themes around children, creativity or personal projects.",
    },
    "health": {
        "teen": "This chapter asks for steadier routines rather than neglecting small wellbeing signals.",
        "adult": "This chapter asks for steadier routines rather than neglecting small wellbeing signals.",
        "senior": "This chapter emphasizes rest, routine and preserving wellbeing.",
    },
    "learning": {
        "teen": "This chapter favours structured learning and guidance over quick shortcuts.",
        "adult": "This chapter favours structured learning and guidance over quick shortcuts.",
    },
    "inner": {
        "adult": "This chapter can heighten the need for personal space and clearer priorities.",
    },
}

_CHAPTER_DEFAULT = "This chapter emphasizes steady progress and consistent effort in this area."


def _chapter_band(band: str) -> str:
    b = (band or "adult").lower()
    if b in ("child", "teen", "young_adult", "adult", "mature_adult", "senior"):
        return b
    return "adult"


def planet_influence_line(planet: str) -> str:
    return PLANET_INFLUENCE.get(planet, f"{planet} is active in this area right now.")


def trajectory_explain(direction: str, area: str = "", *,
                       planet: str = "", variant: int = 0,
                       age_band: str = "") -> str:
    """Human interpretation for a dated trajectory / future window.

    Prefer manifestation renderer when available; this remains a template
    fallback keyed by area×direction×age_band.
    """
    area = (area or "").lower()
    direction = direction if direction in ("up", "mixed", "down") else "mixed"

    if age_band in ("child", "teen") and area == "career":
        teen_up = [
            "Teachers or mentors are more likely to notice consistent effort during this stretch.",
            "Study and school responsibilities can move forward more easily in this stretch.",
        ]
        teen_mixed = [
            "Study responsibilities may need more steady attention than sudden leaps.",
            "Progress comes through consistent effort and teacher recognition rather than shortcuts.",
        ]
        teen_down = [
            "School or study pressure may feel heavier. Steady routines help more than forcing a breakthrough.",
        ]
        pool = {"up": teen_up, "mixed": teen_mixed, "down": teen_down}.get(direction) or teen_mixed
        return pool[int(variant) % len(pool)]

    if age_band == "young_adult" and area == "career":
        ya_up = [
            "Your studies, first professional responsibilities or developing career direction can become more visible during this phase. Use the opening to take ownership of work that has visible impact.",
            "Useful openings can arrive through mentors, classmates or early professional contacts.",
        ]
        ya_mixed = [
            "Study or early-work effort can become more noticeable, even if recognition arrives later than the effort.",
            "Progress is possible through consistent ownership rather than one dramatic breakthrough.",
        ]
        ya_down = [
            "Early career or study progress may feel slower. Strengthen skills and visible results rather than forcing a rushed move.",
        ]
        pool = {"up": ya_up, "mixed": ya_mixed, "down": ya_down}.get(direction) or ya_mixed
        return pool[int(variant) % len(pool)]

    variants = (AREA_TRAJECTORY_VARIANTS.get(area) or {}).get(direction) or []
    if variants:
        bump = {"Saturn": 1, "Jupiter": 0, "Rahu": 2, "Ketu": 2,
                "Mars": 1, "Venus": 0, "Sun": 0, "Moon": 1,
                "Mercury": 2}.get(planet or "", 0)
        idx = (int(variant) + bump) % len(variants)
        return variants[idx]
    return TRAJECTORY_EXPLAIN.get(direction, TRAJECTORY_EXPLAIN["mixed"])


def expect_explain(direction: str, area: str = "", *, age_band: str = "") -> str:
    area = (area or "").lower()
    if age_band:
        try:
            from narration.stage_actions import expect_for_stage
            line = expect_for_stage(area, age_band, direction)
            if line:
                return line
        except Exception:  # noqa: BLE001
            pass
    by_area = AREA_EXPECT.get(area) or {}
    if direction in by_area:
        line = by_area[direction]
        if age_band in ("child", "teen") and area == "career":
            if direction == "mixed":
                return ("Progress may come through steady effort and teacher "
                        "recognition rather than one sudden breakthrough.")
            if direction == "up":
                return "Study and school responsibilities can move forward more easily now."
        if age_band == "young_adult" and area == "career":
            if direction == "up":
                return ("Studies, skills or early professional responsibilities "
                        "can become more visible now.")
            if direction == "mixed":
                return ("Early career progress is possible, though recognition may "
                        "arrive more slowly than the effort.")
        if age_band in ("child", "teen") and area == "health" and direction == "mixed":
            return "Sleep, routine and energy deserve more consistent attention."
        return line
    return trajectory_explain(direction, area, age_band=age_band)


def chapter_area_line(area: str, *, age_band: str = "adult") -> str:
    key = (area or "").lower()
    band = _chapter_band(age_band)
    area_map = CHAPTER_AREA_LINE.get(key) or {}
    if isinstance(area_map, str):
        return area_map
    if band in area_map:
        return area_map[band]
    for fallback in ("adult", "mature_adult", "young_adult", "teen"):
        if fallback in area_map:
            return area_map[fallback]
    return _CHAPTER_DEFAULT


def why_block_html(why_text: str, agreement: str = "") -> str:
    """Render a structured Why section as compact paragraphs."""
    import html as _html
    lines = [ln.strip() for ln in (why_text or "").splitlines() if ln.strip()]
    if not lines and not agreement:
        return ""
    body = "".join(f"<p>{_html.escape(ln)}</p>" for ln in lines)
    agree = (f'<p class="pred-agree">{_html.escape(agreement)}</p>'
             if agreement else "")
    return body + agree
