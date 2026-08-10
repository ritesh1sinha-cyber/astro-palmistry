"""Stage-aware practical actions and expect strings."""

from __future__ import annotations

STAGE_ACTIONS: dict[str, dict[str, str]] = {
    "career": {
        "child": "Use this window to give steady effort to school responsibilities and let a teacher or mentor see your progress.",
        "teen": "Use this window to show consistent effort on studies or projects and ask a teacher or mentor for guidance when needed.",
        "young_adult": "Use this window to take ownership of study or early work that has visible impact and seek guidance from experienced people.",
        "adult": "Use this window to show your work, ask for the responsibility you want, and follow important conversations in writing.",
        "mature_adult": "Use this window to strengthen your position through visible results and experienced sponsorship.",
        "senior": "Use this window to share experience, mentor others, and finish what still deserves your name on it.",
    },
    "money": {
        "child": "Use this phase to notice how resources are managed at home and build steady habits around what you receive.",
        "teen": "Use this phase to build careful money habits and avoid stretching beyond what you can manage.",
        "young_adult": "Use the easier phase to strengthen savings and reduce money that quietly leaks away.",
        "adult": "Use the easier phase to strengthen savings and reduce money that quietly leaks away.",
        "mature_adult": "Use this phase to protect stability and avoid unnecessary financial stretch.",
        "senior": "Use this phase to preserve what you have built and keep commitments manageable.",
    },
    "love": {
        "child": "Use the warmer phase to clear up misunderstandings early with friends or family.",
        "teen": "Use the warmer phase to have the conversation you have been postponing with a friend or close peer.",
        "young_adult": "Use the warmer phase to have the conversation you have been postponing and make time for the relationship.",
        "adult": "Use the warmer phase to have the conversation you have been postponing and make time for the relationship.",
        "mature_adult": "Use this phase to repair goodwill before pressing a difficult request.",
        "senior": "Use this phase to protect companionship through patient, clear conversation.",
    },
    "home": {
        "child": "Use the stable phase to help with one recurring family responsibility at home.",
        "teen": "Use the stable phase to settle recurring home matters and strengthen your family routine.",
        "young_adult": "Use the stable phase to settle recurring home matters and strengthen your family routine.",
        "adult": "Use the stable phase to settle recurring home matters and strengthen your family routine.",
        "mature_adult": "Use this phase to settle household matters with patience and clear follow-through.",
        "senior": "Use this phase to keep home matters calm and manageable.",
    },
    "children": {
        "child": "Use this phase for a creative project or activity that lets you learn through doing.",
        "teen": "Encourage progress on projects without rushing it. Consistency helps more than pressure.",
        "young_adult": "Use this phase to develop a personal project or creative skill steadily.",
        "adult": "Encourage progress without rushing it. Consistency will help more than pressure.",
        "mature_adult": "Support steady progress in family or creative matters without forcing pace.",
        "senior": "Use this phase to encourage family projects or creative continuity with patience.",
    },
    "health": {
        "child": "Use this phase to keep sleep, routine and energy steadier than usual.",
        "teen": "Use this phase to keep sleep, routine and energy steadier than usual.",
        "young_adult": "Use the stronger phase to build routines that keep your energy steady.",
        "adult": "Use the stronger phase to build the routines that keep your energy steady, rather than assuming you can always push harder.",
        "mature_adult": "Use this phase for steady routine, rest and preventive habits.",
        "senior": "Use this phase for routine, rest and timely follow-up rather than pushing through fatigue.",
    },
    "learning": {
        "child": "Use the opening to learn something useful and apply it right away.",
        "teen": "Use the opening to learn something useful and apply it immediately instead of only collecting information.",
        "young_adult": "Use the opening to learn something useful and apply it immediately instead of only collecting information.",
        "adult": "Use the opening to learn something useful and apply it immediately instead of only collecting information.",
        "mature_adult": "Use this phase to revisit difficult material with help from someone experienced.",
        "senior": "Use this phase for steady learning or mental engagement rather than forcing pace.",
    },
    "inner": {
        "child": "Use the quieter phase to notice what actually deserves your energy.",
        "teen": "Use the quieter phase for reflection instead of forcing every answer.",
        "young_adult": "Use the quieter phase for reflection, learning or spiritual practice instead of forcing every answer.",
        "adult": "Use the quieter phase for reflection, learning or spiritual practice instead of forcing every answer.",
        "mature_adult": "Use this phase to withdraw from noise and decide what deserves your energy.",
        "senior": "Use this phase for reflection, peace and deciding what still matters most.",
    },
}

STAGE_EXPECT: dict[str, dict[str, dict[str, str]]] = {
    "career": {
        "child": {"up": "School responsibilities can move forward more easily now.",
                  "mixed": "Study progress may need steady effort rather than one sudden breakthrough.",
                  "down": "School or activity pressure may feel heavier than support."},
        "teen": {"up": "Study and school responsibilities can move forward more easily now.",
                 "mixed": "Progress may come through steady effort and teacher recognition rather than shortcuts.",
                 "down": "Study pressure may feel heavier; routines help more than forcing pace."},
        "young_adult": {"up": "Studies, skills or early professional responsibilities can become more visible now.",
                        "mixed": "Early career progress is possible, though recognition may arrive more slowly than the effort.",
                        "down": "Early work or study progress may feel slower; strengthen skills and visible results."},
    },
    "love": {
        "child": {"up": "Friendships and family bonds may feel easier to manage.",
                  "mixed": "Communication with friends or family may need more patience.",
                  "down": "Close bonds may need extra care and clearer conversation."},
        "teen": {"up": "Friendships may feel easier to reconnect and manage.",
                 "mixed": "Communication with friends or close peers may need more patience.",
                 "down": "Friendships may need extra care; say the awkward thing early."},
        "young_adult": {"up": "Connection and goodwill are easier to rebuild when conversations stay clear.",
                        "mixed": "Communication matters more than intensity during this phase.",
                        "down": "Small misunderstandings can carry more weight than usual."},
    },
    "money": {
        "child": {"up": "Family resources may feel easier to manage.",
                  "mixed": "Resource habits may need more consistent attention.",
                  "down": "Shared resources or expenses may need more careful handling."},
        "teen": {"up": "Allowance, gifts or family resources may feel easier to manage.",
                 "mixed": "Money habits may need more consistent attention than usual.",
                 "down": "Shared expenses or resource pressure may need more care."},
        "young_adult": {"up": "This is a better stretch for strengthening savings and practical cash-flow decisions.",
                        "mixed": "Income can remain manageable, but larger gains need disciplined decisions.",
                        "down": "Protect cash flow and avoid unnecessary financial commitments."},
    },
    "children": {
        "child": {"up": "Creative projects or activities can move forward more easily.",
                  "mixed": "Projects may need patience and steady attention.",
                  "down": "Creative or activity progress may feel uneven."},
        "teen": {"up": "Personal projects or creative work can move forward more easily.",
                 "mixed": "Project progress may be real but uneven — patience helps.",
                 "down": "Projects may need repetition before progress shows."},
        "young_adult": {"up": "Creative or personal projects can move forward with steady support.",
                        "mixed": "Progress around projects is real but uneven.",
                        "down": "Focus on patience and practical help rather than forcing a breakthrough."},
    },
}


def action_for_stage(area: str, band: str, *, direction: str = "up") -> str:
    by_area = STAGE_ACTIONS.get(area) or STAGE_ACTIONS.get("inner", {})
    return by_area.get(band) or by_area.get("adult", "")


def expect_for_stage(area: str, band: str, direction: str) -> str:
    by_area = STAGE_EXPECT.get(area) or {}
    by_band = by_area.get(band) or {}
    return by_band.get(direction, "")
