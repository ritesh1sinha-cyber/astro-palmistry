"""Semantic sentence variants keyed by manifestation — not area+verdict alone."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from interpretation.prediction_meaning import PredictionMeaning

# Past-tense headlines for past validation (may have / noticed framing).
PAST_HEADLINES: dict[tuple[str, str, str], list[str]] = {
    # (narrative_area, manifestation, direction) -> variants
    ("career", "visibility", "up"): [
        "Your work may have become easier to move forward, and people were more likely to notice you.",
        "Your effort may have become more visible during this period.",
        "Responsibilities may have moved forward more easily than before.",
    ],
    ("career", "recognition", "up"): [
        "Recognition may have started catching up with the work you were already doing.",
        "Your work may have received more attention than usual.",
    ],
    ("career", "delayed_reward", "mixed"): [
        "Work may have moved forward, but recognition may have lagged behind the effort.",
        "Progress may have been real, yet the reward may have taken longer to show.",
    ],
    ("career", "delayed_reward", "up"): [
        "Work may have moved forward steadily, even if recognition arrived more slowly.",
        "Progress may have been real, with the full reward taking longer to show.",
    ],
    ("career", "mentor_support", "up"): [
        "Experienced guidance or sponsorship may have helped your work move forward.",
        "A senior person or mentor may have made professional progress easier.",
    ],
    ("career", "network_gain", "up"): [
        "Useful opportunities may have arrived through people already in your network.",
        "An existing contact or group connection may have opened a more practical door.",
    ],
    ("career", "network_gain", "mixed"): [
        "Network openings may have been present, though results may have taken longer to settle.",
    ],
    ("career", "opportunity", "up"): [
        "A practical opportunity may have become easier to act on during this window.",
    ],
    ("career", "responsibility", "mixed"): [
        "Work became harder to ignore. Progress was possible, but it asked for extra effort.",
        "Responsibility may have increased before the results became obvious.",
    ],
    ("career", "competition", "down"): [
        "Work asked more from you than usual. Pressure was clearer than ease.",
        "Professional pressure may have felt heavier than support during this window.",
    ],
    ("early_career", "visibility", "up"): [
        "Your studies, first professional responsibilities or developing career direction may have become more visible.",
        "Effort in study or early work may have been easier for others to notice.",
    ],
    ("early_career", "visibility", "mixed"): [
        "Study or early-work effort may have been solid even when recognition was slower.",
    ],
    ("early_career", "network_gain", "up"): [
        "Useful openings may have come through classmates, mentors or early professional contacts.",
    ],
    ("early_career", "mentor_support", "up"): [
        "Guidance from a mentor or experienced person may have made this period more productive.",
    ],
    ("early_career", "responsibility", "mixed"): [
        "First professional or study responsibilities may have needed more organization than usual.",
    ],
    ("early_career", "delayed_reward", "up"): [
        "Progress in study or early work may have been real, with recognition arriving more slowly.",
    ],
    ("education", "teacher_recognition", "up"): [
        "Your studies or responsibilities may have received more attention from teachers or mentors.",
        "Your effort may have been noticed more easily by people who guide your learning.",
    ],
    ("education", "study_progress", "up"): [
        "Study or school responsibilities may have moved forward more easily than before.",
        "Learning tasks may have felt more manageable during this period.",
    ],
    ("education", "responsibility", "mixed"): [
        "School or study responsibilities may have needed more effort than usual.",
        "Progress may have been possible, but it may have required steady attention.",
    ],
    ("education", "mentor_support", "up"): [
        "Guidance from a teacher or mentor may have made this period more productive.",
    ],
    ("health", "routine", "mixed"): [
        "Maintaining sleep, routine and follow-up may have felt more important.",
        "Energy and routine may have needed more consistent attention.",
    ],
    ("health", "rest", "mixed"): [
        "Rest and recovery may have felt more necessary than usual.",
    ],
    ("health", "preventive_attention", "mixed"): [
        "Preventive habits and steady routines may have mattered more than pushing hard.",
    ],
    ("love", "communication", "mixed"): [
        "Communication in close relationships may have needed more patience than usual.",
    ],
    ("friendships", "communication", "mixed"): [
        "Communication with friends or close peers may have needed more patience.",
    ],
    ("money", "cash_flow", "mixed"): [
        "Money was moving, but not always staying where you wanted it.",
    ],
    ("resources", "family_finances", "mixed"): [
        "Family money matters or shared resources may have needed more attention.",
    ],
    ("inner", "space", "mixed"): [
        "You may have wanted more personal space while deciding what deserved your energy.",
    ],
    ("home", "family_responsibility", "mixed"): [
        "A family responsibility may have needed more of your attention than usual.",
    ],
    ("learning", "teacher_support", "up"): [
        "Teachers, mentors or structured learning may have opened useful doors.",
    ],
}

# Present/current headlines for cards.
CURRENT_HEADLINES: dict[tuple[str, str, str], list[str]] = {
    ("career", "visibility", "mixed"): [
        "The work is solid; recognition may be slower than the effort you are putting in.",
        "Your effort can move forward, although recognition may take longer to catch up.",
    ],
    ("career", "delayed_reward", "mixed"): [
        "The work is solid; the recognition is slower than the work. Both are true at once.",
        "Progress is possible, but the reward may arrive more slowly than the effort.",
    ],
    ("career", "responsibility", "mixed"): [
        "More responsibility may be visible before the reward becomes obvious.",
    ],
    ("career", "mentor_support", "up"): [
        "Progress comes more easily when you use experienced guidance and sponsorship.",
    ],
    ("career", "visibility", "up"): [
        "Your work can become more visible during this phase, although recognition may take longer than the effort itself.",
        "Use this opening to take ownership of work that has visible impact.",
    ],
    ("career", "network_gain", "up"): [
        "Useful opportunities can come through people already in your network, especially when you stay open to practical collaboration.",
        "An existing contact or group circle can become more useful during this phase.",
    ],
    ("career", "network_gain", "mixed"): [
        "Network openings are present, but results still depend on careful follow-through.",
    ],
    ("early_career", "visibility", "up"): [
        "Your studies, first professional responsibilities or developing career direction can become more visible during this phase.",
        "Use the opening to take ownership of study or early work that has visible impact.",
    ],
    ("early_career", "visibility", "mixed"): [
        "Study or early-work effort can stay solid even when recognition arrives slowly.",
    ],
    ("early_career", "network_gain", "up"): [
        "Useful openings can arrive through mentors, classmates or early professional contacts.",
    ],
    ("early_career", "mentor_support", "up"): [
        "Guidance from experienced people can make this stretch more productive.",
    ],
    ("early_career", "delayed_reward", "mixed"): [
        "Progress in study or early work is possible, but recognition may take longer than the effort.",
    ],
    ("education", "teacher_recognition", "mixed"): [
        "Your effort is more likely to be noticed by teachers or mentors than through shortcuts.",
    ],
    ("education", "study_progress", "up"): [
        "Study and school responsibilities can move forward more easily in this stretch.",
    ],
    ("health", "routine", "mixed"): [
        "This phase is better handled through consistency than extremes. Sleep and routine deserve attention.",
    ],
    ("health", "preventive_attention", "mixed"): [
        "Energy and routine respond better to steady habits than to pushing through fatigue.",
    ],
    ("health", "rest", "down"): [
        "Rest is not optional in this stretch. Protecting recovery helps more than forcing pace.",
    ],
}

# Manifestation bullets — past tense, evidence-specific.
PAST_MANIFESTS: dict[tuple[str, str], list[str]] = {
    ("career", "visibility"): [
        "your work receiving more attention",
        "a responsibility becoming more visible",
        "a senior person taking greater notice",
        "work being reviewed or evaluated more closely",
    ],
    ("career", "recognition"): [
        "recognition for work you had already completed",
        "a senior person noticing your effort",
        "greater visibility for results others could see",
    ],
    ("career", "authority"): [
        "being trusted with a more visible responsibility",
        "a leadership opportunity becoming clearer",
        "authority in a project mattering more than before",
    ],
    ("career", "leadership"): [
        "a leadership opportunity",
        "being asked to take charge of a visible piece of work",
    ],
    ("career", "network_gain"): [
        "an existing contact becoming useful",
        "an opportunity arriving through your network",
        "wider attention from a group",
        "a useful connection opening a door",
    ],
    ("career", "opportunity"): [
        "a practical opportunity becoming easier to act on",
        "effort producing a more tangible result",
        "an opening through people already around you",
    ],
    ("career", "gains"): [
        "effort producing a tangible result",
        "a useful outcome arriving through contacts",
    ],
    ("career", "support_from_contacts"): [
        "support from people already in your circle",
        "a contact offering a practical introduction",
    ],
    ("career", "delayed_reward"): [
        "progress after a period of waiting",
        "responsibility increasing before reward",
        "something important requiring persistence",
    ],
    ("career", "mentor_support"): [
        "useful guidance from an experienced person",
        "support from a teacher, mentor or senior",
        "an opportunity created through guidance",
    ],
    ("career", "responsibility"): [
        "more responsibility becoming visible",
        "carrying extra ownership before results showed",
        "a project demanding steadier follow-through",
    ],
    ("early_career", "visibility"): [
        "study or early-work effort receiving more attention",
        "a responsibility in a project becoming more visible",
        "a mentor or supervisor taking greater notice",
    ],
    ("early_career", "network_gain"): [
        "an existing classmate or contact becoming useful",
        "an opportunity through early professional or college networks",
        "wider attention from a group or team",
    ],
    ("early_career", "mentor_support"): [
        "useful guidance from a mentor or experienced person",
        "support from a teacher or senior colleague",
    ],
    ("early_career", "responsibility"): [
        "first professional or study responsibilities needing more organization",
        "being trusted with a deadline or project task",
    ],
    ("early_career", "delayed_reward"): [
        "progress after persistence in study or early work",
        "responsibility arriving before recognition",
    ],
    ("education", "teacher_recognition"): [
        "a teacher noticing improvement",
        "being trusted with a responsibility",
        "a mentor offering useful guidance",
    ],
    ("education", "study_progress"): [
        "a school project moving forward",
        "study tasks becoming more manageable",
        "improvement after extra effort",
    ],
    ("education", "responsibility"): [
        "taking on a school or study responsibility",
        "being asked to lead or organise something",
        "managing deadlines more carefully",
    ],
    ("education", "mentor_support"): [
        "useful guidance from a teacher or mentor",
        "support that made study progress easier",
    ],
    ("health", "routine"): [
        "paying more attention to sleep or routine",
        "trying to keep habits steadier than usual",
        "noticing when energy dropped faster",
    ],
    ("health", "rest"): [
        "needing more rest than usual",
        "stepping back when energy felt low",
        "protecting recovery time",
    ],
    ("health", "preventive_attention"): [
        "keeping sleep and routine steadier",
        "giving preventive habits more attention",
    ],
    ("friendships", "communication"): [
        "a conversation that needed patience",
        "clearing up a misunderstanding",
        "needing to say something awkward early",
    ],
    ("love", "communication"): [
        "a conversation that needed patience",
        "a small issue that had to be cleared up",
        "mixed signals that required careful talk",
    ],
    ("inner", "space"): [
        "questioning what deserves your energy",
        "wanting more space from noise",
        "trying to make peace with something unfinished",
    ],
    ("money", "cash_flow"): [
        "higher expenses or family commitments",
        "income arriving in uneven patches",
        "a financial decision that needed patience",
    ],
    ("resources", "family_finances"): [
        "family money matters needing more attention",
        "shared resources requiring careful handling",
    ],
    ("resources", "resource_habits"): [
        "spending or saving habits needing more care",
        "learning to manage what you already have",
    ],
    ("home", "family_responsibility"): [
        "a family matter needing patience",
        "a household decision taking longer to settle",
        "one recurring responsibility pulling attention",
    ],
    ("learning", "teacher_support"): [
        "a teacher or mentor making progress easier",
        "structured learning paying off",
        "revisiting difficult material with help",
    ],
}

# Future / trajectory headlines (same meaning model, forward tense).
FUTURE_HEADLINES: dict[tuple[str, str, str], list[str]] = {
    ("career", "visibility", "up"): [
        "Your work can become more visible during this phase. Use the opening to take ownership of work that has visible impact.",
        "Recognition is easier when you keep your work visible and document results others can see.",
    ],
    ("career", "visibility", "mixed"): [
        "Your work can become more visible during this phase, although recognition may take longer than the effort itself.",
        "Progress is possible, but it is more likely through consistent ownership than one dramatic breakthrough.",
    ],
    ("career", "network_gain", "up"): [
        "Useful opportunities can come through people already in your network, especially when you stay open to practical collaboration.",
    ],
    ("career", "network_gain", "mixed"): [
        "Network openings can appear, but results still depend on careful follow-through rather than assuming an automatic gain.",
    ],
    ("career", "delayed_reward", "mixed"): [
        "Progress is possible, but the reward may arrive more slowly than the effort.",
        "Responsibility may increase before recognition catches up.",
    ],
    ("career", "mentor_support", "up"): [
        "Progress comes more easily when you use experienced guidance and sponsorship.",
    ],
    ("early_career", "visibility", "up"): [
        "Your studies, first professional responsibilities or developing career direction can become more visible during this phase. Use the opening to take ownership of work that has visible impact.",
    ],
    ("early_career", "visibility", "mixed"): [
        "Study or early-work effort can become more noticeable, even if recognition arrives later than the effort.",
    ],
    ("early_career", "network_gain", "up"): [
        "Useful openings can arrive through mentors, classmates or early professional contacts.",
    ],
    ("education", "teacher_recognition", "up"): [
        "Teachers or mentors are more likely to notice consistent effort during this stretch.",
    ],
    ("education", "study_progress", "up"): [
        "Study and school responsibilities can move forward more easily in this stretch.",
    ],
    ("health", "routine", "mixed"): [
        "This phase may make rest, routine and energy management more important.",
        "Maintaining sleep, consistency and timely follow-up deserves more attention during this period.",
    ],
    ("health", "preventive_attention", "mixed"): [
        "Use this phase to strengthen sleep, food, movement and other daily routines.",
    ],
    ("money", "cash_flow", "mixed"): [
        "Income can remain manageable, but larger gains are more likely through disciplined decisions than quick opportunities.",
    ],
    ("money", "income", "up"): [
        "This is a better stretch for strengthening savings and practical cash-flow decisions.",
    ],
    ("resources", "resource_habits", "mixed"): [
        "Resource and money habits deserve more consistent attention during this phase.",
    ],
    ("resources", "family_finances", "mixed"): [
        "Family money matters or shared resources may need more careful handling in this stretch.",
    ],
    ("home", "family_responsibility", "mixed"): [
        "Home is mostly workable, but one recurring responsibility may still pull attention.",
    ],
    ("learning", "teacher_support", "up"): [
        "Teachers, mentors or structured learning can open useful doors in this stretch.",
    ],
    ("learning", "study", "up"): [
        "Study and skill-building can move forward more easily when effort stays consistent.",
    ],
    ("love", "communication", "mixed"): [
        "Communication matters more than intensity during this phase. Small misunderstandings can become larger if left unresolved.",
    ],
    ("friendships", "communication", "mixed"): [
        "Communication with friends or close peers may need more patience during this phase.",
    ],
}


def pick_variant(key: tuple, table: dict, variant_index: int = 0) -> str:
    options = table.get(key) or []
    if not options:
        return ""
    return options[variant_index % len(options)]


def headline_key(meaning: "PredictionMeaning", *, past: bool = True) -> tuple:
    primary = meaning.manifestations[0] if meaning.manifestations else "responsibility"
    return (meaning.narrative_area, primary, meaning.direction)


def manifest_keys(meaning: "PredictionMeaning") -> list[tuple[str, str]]:
    domain = meaning.narrative_area
    return [(domain, m) for m in meaning.manifestations[:2]]
