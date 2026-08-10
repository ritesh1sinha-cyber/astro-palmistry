"""Recognition prose from manifestation IDs × age band — Level-2 pattern language only."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from interpretation.prediction_meaning import PredictionMeaning

# (manifestation_id, band) -> soft pattern claim (Level 2 default)
RECOGNITION_CLAIMS: dict[tuple[str, str], str] = {
    # Money / resources
    ("resource_habits", "child"): "You may have become aware early of how resources are managed, saved or spent in your family.",
    ("resource_habits", "teen"): "You may have become more aware of how money, allowance and family resources are handled than many peers.",
    ("allowance", "teen"): "You may have become more careful about allowance, gifts and small savings as responsibilities grew.",
    ("resource_habits", "young_adult"): "Financial independence may have developed gradually, with each step teaching you how to manage resources more carefully.",
    ("family_finances", "child"): "You may have learned early that effort and learning matter more than shortcuts.",
    ("family_finances", "teen"): "Your strengths may have been noticed more through study, projects or skills than through possessions.",
    ("income", "young_adult"): "Financial independence may have developed gradually as skills and responsibilities grew.",
    ("income", "adult"): "Financial progress may have come in stages, with each improvement requiring persistence.",
    ("income", "mature_adult"): "Money may have tended to arrive in steps rather than all at once, and each step followed sustained effort.",
    ("financial_stability", "senior"): "Financial stability may have been built gradually, making preservation and careful management increasingly important.",
    ("savings", "teen"): "You may have learned to hold onto allowance, gifts or prizes more carefully as responsibilities increased.",
    ("savings", "adult"): "What you managed to keep may have mattered as much as what arrived — saving may have taken more discipline than spending.",
    ("savings", "mature_adult"): "Preserving what you built may have required more discipline than acquiring it in the first place.",
    ("cash_flow", "adult"): "Financial support may have arrived when you needed it, sometimes from unexpected people or timing.",
    ("network_gain", "adult"): "Useful opportunities may have come through people already in your network.",
    ("gains", "adult"): "Results from your wider network may have become more tangible over time.",
    ("delayed_reward", "adult"): "Financial progress may have come in stages, with each improvement requiring persistence.",
    # Love / friendships
    ("communication", "child"): "Close bonds may have carried a private difficulty that you did not talk about openly.",
    ("communication", "teen"): "Friendships or close bonds may have carried a private difficulty that others did not see.",
    ("communication", "adult"): "Close relationships may have carried a private difficulty that you handled without telling many people.",
    ("emotional_support", "child"): "Warmth from friends or family may have been easier to find than choosing wisely among many options.",
    ("emotional_support", "teen"): "Friendships may have been easier to find than choosing wisely among many options.",
    ("emotional_support", "adult"): "Affection may have been easier to find; choosing well from what was offered was the harder part.",
    ("commitment", "young_adult"): "There may have been at least one attachment you kept largely to yourself.",
    ("commitment", "adult"): "There may have been at least one attachment you kept largely to yourself.",
    ("distance", "teen"): "Friendships may sometimes become intense quickly, especially when you feel strongly about someone.",
    ("distance", "adult"): "Arguments in close relationships may flare quickly; clear communication may matter more than intensity.",
    ("reconnection", "teen"): "Friendships may have asked more work of you than they seemed to ask of other people.",
    ("reconnection", "adult"): "Relationships may have asked more work of you than they seemed to ask of others.",
    ("expectation_management", "teen"): "Friendships may have needed more patience and clear communication than intensity alone.",
    # Career / education
    ("study_progress", "child"): "Structured institutions, authority figures or expectations around achievement may have had a noticeable influence on your path.",
    ("study_progress", "teen"): "Schools, teachers or structured institutions may have shaped expectations around achievement more than you expected.",
    ("teacher_recognition", "teen"): "Teachers or mentors may have noticed your effort before results fully showed.",
    ("teacher_recognition", "child"): "Achievement and responsibility may have shown through school and activities.",
    ("visibility", "young_adult"): "Early effort in study or work may have become more visible to teachers, mentors or peers.",
    ("visibility", "adult"): "Recognition may have started catching up with the work you were already doing.",
    ("responsibility", "teen"): "Responsibility may have increased before recognition fully caught up with your effort.",
    ("responsibility", "adult"): "Responsibility may have increased before recognition fully caught up with your effort.",
    ("responsibility", "child"): "People may have turned to you when something went wrong, even when you were still learning.",
    ("mentor_support", "teen"): "Guidance from a teacher or mentor may have made a demanding stretch more manageable.",
    ("mentor_support", "adult"): "Experienced guidance or sponsorship may have helped your work move forward during a demanding stretch.",
    ("mentor_support", "senior"): "Others may look to you for steady guidance built from long experience.",
    ("leadership", "mature_adult"): "Leadership and authority may have grown through sustained responsibility rather than quick promotion.",
    ("legacy", "senior"): "What you built may matter more through influence and mentoring than through new titles.",
    ("achievement", "child"): "Achievement and responsibility may have shown through school and activities.",
    ("recognition", "adult"): "Recognition may have started catching up with the work you were already doing.",
    ("network_gain", "young_adult"): "Useful openings may have come through classmates, mentors or early contacts.",
    ("opportunity", "young_adult"): "A practical opportunity may have become easier to act on during an early-career stretch.",
    ("delayed_recognition", "adult"): "Progress may have been real, yet the full reward may have taken longer to show.",
    # Health — wellbeing only
    ("energy_management", "child"): "You may have become aware that rest and steady routine help you handle demanding stretches.",
    ("energy_management", "teen"): "You may have become more aware that rest and steady routine help you handle demanding stretches.",
    ("energy_management", "adult"): "You may find that consistent routines help you recover from demanding periods.",
    ("routine", "child"): "Consistency in rest and routine may matter more for you than for some peers.",
    ("routine", "teen"): "Changes in routine or stress may make you more aware of your energy and physical wellbeing.",
    ("routine", "adult"): "Changes in routine or stress may make you more aware of how closely your emotional state, routine and physical wellbeing are connected.",
    ("rest", "senior"): "Rest and steady routine may be particularly important for maintaining wellbeing.",
    ("stress_management", "teen"): "Stress may make you more aware of how closely your emotional state, routine and physical wellbeing are connected.",
    ("stress_management", "adult"): "Consistency, rest and timely follow-up may be particularly important during demanding periods.",
    ("preventive_attention", "adult"): "Paying attention to rest and routine may have helped you stay steadier during demanding stretches.",
    ("wellbeing", "senior"): "Preserving energy through rest and routine may matter more than pushing through every demand.",
    # Home / parents
    ("family_responsibility", "child"): "Responsibility may have landed on you earlier than it should have.",
    ("family_responsibility", "teen"): "Responsibility may have landed on you earlier than you were ready for.",
    ("family_responsibility", "adult"): "Responsibility may have landed on you earlier than you were ready for.",
    ("domestic_stability", "child"): "Whatever else was going on, you may have had one steady place to come back to.",
    ("domestic_stability", "teen"): "Whatever else was going on, you may have had one steady place to come back to.",
    ("domestic_stability", "adult"): "Whatever else was going on, you may have had one steady place to come back to.",
}

# Recognition bullets from manifestation IDs (not invented events)
RECOGNITION_BULLETS: dict[str, list[str]] = {
    # Money — never use career-responsibility bullets here.
    "resource_habits": ["becoming more careful about spending", "learning to save", "becoming aware of family resource decisions"],
    "income": ["income improving gradually", "earning becoming more dependent on consistency", "financial progress building in stages"],
    "financial_progress": ["financial progress building in stages", "results following sustained effort", "practical decisions making a difference over time"],
    "savings": ["holding onto what reaches you", "learning to value what you already have", "preserving resources after they are acquired"],
    "financial_retention": ["preserving what you built", "becoming more deliberate about what you keep", "valuing stability alongside growth"],
    "resource_discipline": ["careful handling of resources", "making practical financial decisions", "avoiding unnecessary leakage of resources"],
    "financial_stability": ["stability becoming more important over time", "building a dependable financial base", "protecting accumulated resources"],
    "cash_flow": ["managing uneven inflows and outflows", "timing becoming important in financial decisions", "keeping enough flexibility between income and expenses"],
    "network_gain": ["an existing contact becoming useful", "opportunities through colleagues or mentors", "support arriving through your wider network"],
    "gains": ["results becoming more tangible", "benefits from wider networks", "opportunities converting into practical gains"],

    # Career / education
    "study_progress": ["teachers or mentors noticing effort", "school responsibilities needing more organization", "steady learning producing visible progress"],
    "teacher_recognition": ["effort being noticed before full results showed", "structured learning paying off", "encouragement from a teacher or mentor"],
    "visibility": ["effort becoming more visible", "recognition catching up with work already done", "results being easier for others to notice"],
    "responsibility": ["greater responsibility before reward", "persistence mattering more than shortcuts", "being trusted with important work"],
    "career_responsibility": ["greater responsibility before reward", "being trusted with important work", "authority building through sustained effort"],
    "recognition": ["recognition arriving after sustained effort", "progress becoming more visible", "contribution receiving greater attention"],
    "delayed_recognition": ["effort continuing before recognition caught up", "results taking longer to become visible", "patience being rewarded over time"],
    "delayed_reward": ["progress preceding the full reward", "results taking time to become tangible", "consistency mattering before payoff"],
    "career_transition": ["a change in role or direction", "re-establishing yourself in a new chapter", "learning from a professional detour"],
    "leadership": ["being trusted to make decisions", "others relying on your judgment", "authority growing through responsibility"],
    "authority": ["greater decision-making responsibility", "being trusted in important situations", "professional standing growing over time"],
    "mentor_support": ["guidance from an experienced person or professional contact", "sponsorship or an introduction opening a practical door", "learning from someone further along"],
    "support_from_contacts": ["an existing contact becoming useful", "an introduction opening a door", "support arriving through professional relationships"],
    "network_opportunity": ["an opportunity through an existing network", "a useful introduction", "support from colleagues, mentors or contacts"],
    "opportunity": ["a practical opening becoming easier to act on", "timing helping an opportunity become usable", "support making progress easier"],
    "achievement": ["results becoming visible", "effort producing something concrete", "being recognized for what you built"],

    # Relationships
    "communication": ["needing clearer conversations", "private issues being handled quietly", "patience mattering in close bonds"],
    "emotional_support": ["support from friends or family", "warmth being easier to find than choosing wisely", "valuing dependable emotional support"],
    "commitment": ["taking an important bond seriously", "working through differences rather than walking away", "learning what commitment requires"],
    "distance": ["periods of emotional or practical distance", "needing space before reconnecting", "learning when to communicate and when to step back"],
    "reconnection": ["relationships requiring renewed effort", "rebuilding a connection after distance", "patience helping a bond recover"],
    "expectation_management": ["clear expectations preventing friction", "patience mattering more than intensity", "learning to communicate needs directly"],
    "conflict": ["arguments becoming intense when communication is unclear", "learning to handle friction without escalation", "direct conversation reducing misunderstandings"],
    "harmony": ["valuing warmth and cooperation", "relationships becoming steadier through mutual support", "choosing compatibility over intensity"],

    # Health — wellbeing only
    "energy_management": ["noticing when rest or recovery was needed", "becoming more aware of energy limits", "adjusting pace during demanding periods"],
    "routine": ["rest and routine mattering during demanding stretches", "becoming more aware of how routine affected wellbeing", "steady habits supporting day-to-day balance"],
    "rest": ["recognizing the value of recovery", "needing more deliberate rest during pressure", "pace affecting how well you function"],
    "stress_management": ["noticing the effect of pressure on routine", "learning when to slow down", "becoming more aware of the connection between stress and wellbeing"],
    "preventive_attention": ["paying attention before a problem becomes bigger", "timely follow-up becoming useful", "steady routines supporting wellbeing"],
    "wellbeing": ["protecting energy", "keeping steadier routines", "recognizing when recovery matters"],
    "health_routines": ["consistent routines supporting wellbeing", "rest becoming part of performance", "paying attention to energy levels"],
    "slow_recovery": ["allowing more time for recovery", "avoiding the temptation to push through", "steady routine helping recovery"],

    # Home / parents
    "family_responsibility": ["responsibility arriving early", "being the sensible one before feeling ready", "family expectations shaping decisions"],
    "domestic_stability": ["one steady place to return to", "home acting as an anchor", "valuing stability during change"],
    "family_support": ["support from family", "guidance from a parent or elder", "family becoming an anchor during change"],
    "emotional_security": ["needing a dependable home base", "valuing emotional steadiness", "home providing a sense of security"],
}

# Manifestation aliases when a band-specific claim is missing
_MANIFEST_ALIASES: dict[str, str] = {
    "allowance": "resource_habits",
    "savings_habits": "savings",
    "mixed_signal": "responsibility",
}

TAG_EVIDENCE: dict[str, tuple[str, int, str]] = {
    "money_earn": ("money", 11, "Mercury"),
    "money_hold": ("money", 2, "Saturn"),
    "self_made": ("money", 11, "Saturn"),
    "love_delayed": ("love", 7, "Saturn"),
    "love_hot": ("love", 7, "Mars"),
    "career_stage": ("career", 10, "Saturn"),
    "health_outlasts": ("health", 6, "Mars"),
    "health_hard": ("health", 6, "Saturn"),
}

# Extended tag -> (house, planet) for hand-written and 108-rule recognition tags.
CLAIM_EVIDENCE: dict[str, tuple[int, str]] = {
    "money_earn": (11, "Mercury"),
    "money_hold": (2, "Saturn"),
    "self_made": (11, "Saturn"),
    "love_delayed": (7, "Saturn"),
    "love_hot": (7, "Mars"),
    "career_stage": (10, "Saturn"),
    "health_outlasts": (6, "Mars"),
    "health_hard": (6, "Saturn"),
    "health_saturn_6": (6, "Saturn"),
    "health_mars_6": (6, "Mars"),
    "health_node_6": (6, "Rahu"),
    "health_moon_gut": (6, "Moon"),
    "health_sun_vitals": (1, "Sun"),
    "health_jupiter_weight": (6, "Jupiter"),
    "health_sav_6": (6, "Mars"),
    "health_lagna_weak": (1, "Saturn"),
    "health_lagna_strong": (1, "Sun"),
    "money_lord_exchange": (11, "Jupiter"),
    "money_rahu_11": (11, "Rahu"),
    "money_saturn_2": (2, "Saturn"),
    "money_malefic_12": (12, "Saturn"),
    "money_tight": (2, "Saturn"),
    "money_jupiter_wealth": (11, "Jupiter"),
    "money_mercury_earn": (11, "Mercury"),
    "money_sav_earn_hold": (11, "Mercury"),
    "money_sav_hold": (2, "Saturn"),
    "love_lord_dusthana": (7, "Saturn"),
    "love_venus_debilitated": (7, "Venus"),
    "love_venus_strong": (7, "Venus"),
    "love_saturn_7": (7, "Saturn"),
    "love_mars_7": (7, "Mars"),
    "love_sav_7": (7, "Venus"),
    "love_venus_angle": (7, "Venus"),
    "love_venus_hidden": (12, "Venus"),
    "parents_sun_weak": (9, "Sun"),
    "parents_sun_strong": (9, "Sun"),
    "parents_moon_4": (4, "Moon"),
    "parents_4th_dusthana": (4, "Moon"),
    "parents_9th_dusthana": (9, "Jupiter"),
    "parents_saturn_early": (4, "Saturn"),
    "parents_sav_4": (4, "Moon"),
    "money_windfall": (8, "Jupiter"),
    "money_fought_for": (11, "Mars"),
    "money_inheritance": (9, "Jupiter"),
    "money_started_behind": (2, "Saturn"),
    "money_floor": (9, "Jupiter"),
    "money_loss_absorbed": (12, "Saturn"),
    "health_survived": (8, "Saturn"),
    "health_running_fight": (6, "Mars"),
    "mind_steady": (1, "Moon"),
    "survivor": (8, "Saturn"),
    "career_state": (10, "Saturn"),
    "career_vouched": (10, "Jupiter"),
    "career_head": (10, "Mercury"),
    "career_charge": (10, "Mars"),
    "career_initiative": (10, "Mars"),
    "career_reader": (10, "Mercury"),
    "career_early_recognition": (10, "Sun"),
    "career_straight": (10, "Mercury"),
    "career_detour": (10, "Saturn"),
    "adhi_respected": (10, "Jupiter"),
    "adhi_struggle": (6, "Saturn"),
    "home_underresourced": (4, "Moon"),
    "father_diminished": (9, "Sun"),
}


def tag_evidence_house_planet(tag: str) -> tuple[int, str] | None:
    """Resolve (house, planet) evidence for a recognition tag."""
    if tag in CLAIM_EVIDENCE:
        return CLAIM_EVIDENCE[tag]
    te = TAG_EVIDENCE.get(tag)
    if te:
        return (te[1], te[2])
    if tag.startswith("career_stage_"):
        try:
            return (10, "Saturn")
        except ValueError:
            pass
    if tag.startswith("upheaval_"):
        try:
            return (int(tag.rsplit("_", 1)[-1]), "Saturn")
        except ValueError:
            pass
    if tag.startswith("repeat_"):
        try:
            return (int(tag.rsplit("_", 1)[-1]), "Rahu")
        except ValueError:
            pass
    if tag in ("authority", "status"):
        return (10, "Sun")
    return None

_DOMAIN_DEFAULTS: dict[str, tuple[int, str]] = {
    "money": (2, "Saturn"),
    "love": (7, "Venus"),
    "career": (10, "Saturn"),
    "health": (6, "Mars"),
    "parents": (4, "Moon"),
}


# Context-aware claims override the generic manifestation sentence when the
# same ID means something different in different life areas.
CONTEXT_CLAIMS: dict[tuple[str, str, str], str] = {
    ("career", "responsibility", "adult"):
        "You may have taken on more responsibility before the results became fully visible.",
    ("career", "responsibility", "mature_adult"):
        "You may have taken on greater responsibility, with authority building through sustained work.",
    ("career", "responsibility", "senior"):
        "Others may increasingly have relied on your experience and judgment.",
    ("career", "delayed_reward", "adult"):
        "Work may have moved forward, but recognition or reward may have taken longer to catch up.",
    ("career", "delayed_reward", "mature_adult"):
        "Progress may have been real, although recognition or reward may have followed more gradually.",
    ("career", "delayed_reward", "senior"):
        "Important results may have come through persistence and long-term effort rather than quick recognition.",
    ("career", "visibility", "adult"):
        "Your work may have become more visible, especially where results could be clearly seen.",
    ("career", "recognition", "adult"):
        "Your work may have received more recognition or attention than before.",
    ("health", "routine", "adult"):
        "Changes in routine or stress may have made you more aware of how closely rest, energy and wellbeing are connected.",
    ("health", "energy_management", "adult"):
        "You may have become more aware of how rest and energy levels affect your day-to-day wellbeing.",
    ("health", "preventive_attention", "adult"):
        "You may have found that steady routines and timely attention mattered more during demanding stretches.",
    ("health", "stress_management", "adult"):
        "Periods of stress may have made the connection between emotional pressure, routine and wellbeing more noticeable.",
    ("money", "income", "adult"):
        "Financial progress may have developed in stages, with each step requiring practical judgment and consistency.",
    ("money", "cash_flow", "adult"):
        "Money may have moved in uneven stretches, making timing and practical management more important.",
    ("money", "savings", "adult"):
        "Preserving what you built may have mattered almost as much as increasing what came in.",
    ("money", "financial_stability", "adult"):
        "Financial stability may have been built gradually through careful decisions rather than one sudden change.",
}

# When two manifestations belong to the same user-facing progression, render
# one coherent sentence instead of printing two closely related claims.
COMPOSITE_CLAIMS: dict[frozenset[str], dict[str, str]] = {
    frozenset({"responsibility", "recognition"}): {
        "adult": "There may have been periods when responsibility increased before recognition caught up, with your effort becoming more visible over time.",
        "mature_adult": "Responsibility and recognition may have grown together, with authority becoming more visible through sustained work.",
        "senior": "Your experience may have become more visible as responsibility shifted toward guidance, judgment and influence.",
    },
    frozenset({"responsibility", "visibility"}): {
        "adult": "You may have taken on greater responsibility while your work also became more visible to others.",
        "mature_adult": "Greater responsibility may have brought stronger visibility and influence over time.",
        "senior": "Your experience may have become more visible as others increasingly relied on your judgment.",
    },
    frozenset({"responsibility", "delayed_reward"}): {
        "adult": "There may have been periods when responsibility increased before the results or recognition became fully visible.",
        "mature_adult": "Long-term progress may have required carrying responsibility before the full reward became visible.",
        "senior": "Some of your most meaningful results may have come through persistence rather than quick recognition.",
    },
    frozenset({"routine", "energy_management"}): {
        "adult": "Changes in routine may have made you more aware of how rest, energy and overall wellbeing are connected.",
        "teen": "Changes in routine may have made you more aware of how rest and energy affect how you feel and function.",
        "child": "Steady rest and routine may have made a noticeable difference to how you handled demanding stretches.",
    },
    frozenset({"routine", "preventive_attention"}): {
        "adult": "You may have become more aware that steady routines and timely attention help you stay on track during demanding periods.",
    },
    frozenset({"routine", "rest"}): {
        "adult": "Periods of pressure may have made rest and consistent routine more important to your wellbeing.",
    },
    frozenset({"income", "savings"}): {
        "adult": "Financial progress may have developed gradually, with learning to preserve what came in becoming part of the process.",
    },
    frozenset({"income", "financial_stability"}): {
        "adult": "Financial progress may have developed gradually, with stability becoming more important as resources grew.",
    },
    frozenset({"cash_flow", "financial_stability"}): {
        "adult": "Money may have moved through uneven stretches while you gradually built greater financial stability.",
    },
    frozenset({"communication", "commitment"}): {
        "adult": "Close relationships may have needed both clearer communication and a willingness to work through differences.",
    },
}

def _composite_claim(primary: str, secondary: str, band: str) -> Optional[str]:
    if not primary or not secondary:
        return None
    return (COMPOSITE_CLAIMS.get(frozenset((primary, secondary))) or {}).get(band)


def claim_for_manifestation(
    primary: str,
    secondary: str,
    band: str,
    *,
    variant_index: int = 0,
    narrative_area: str = "",
) -> Optional[str]:
    """Render Level-2 recognition claim from validated manifestation IDs.

    Context-specific and composite claims are preferred over generic
    manifestation text so the same ID does not produce the same biography
    in unrelated life areas.
    """
    composite = _composite_claim(primary, secondary, band)
    if composite:
        return composite

    if narrative_area:
        for manifest in (primary, secondary):
            text = CONTEXT_CLAIMS.get((narrative_area, manifest, band))
            if text:
                return text

    keys = []
    for manifest in (primary, secondary):
        for mid in (manifest, _MANIFEST_ALIASES.get(manifest, "")):
            if not mid:
                continue
            keys.append((mid, band))
            if band in ("mature_adult", "senior"):
                keys.append((mid, "adult"))
            if band == "young_adult":
                keys.append((mid, "teen"))
    if variant_index:
        keys = keys[variant_index:] + keys[:variant_index]
    for key in keys:
        if key in RECOGNITION_CLAIMS:
            return RECOGNITION_CLAIMS[key]
    return None


def bullets_for_meaning(meaning: "PredictionMeaning") -> list[str]:
    """Return domain-correct recognition bullets.

    The master manifestation lookup is authoritative when it contains
    recognition_bullets. The legacy local map is only a compatibility
    fallback. Bullets are filtered by narrative area so career bullets cannot
    leak into money/health/network claims.
    """
    try:
        from interpretation.stage_config import manifestation_metadata
    except Exception:
        manifestation_metadata = lambda _mid: {}  # type: ignore

    area = (getattr(meaning, "narrative_area", "") or getattr(meaning, "area", "") or "").lower()
    if area == "resources":
        area = "money"

    out: list[str] = []
    ids = [meaning.primary, meaning.secondary, meaning.caution]

    for mid in ids:
        if not mid:
            continue
        meta = manifestation_metadata(mid) or {}
        bullets = meta.get("recognition_bullets") or []
        if not bullets:
            bullets = RECOGNITION_BULLETS.get(mid, [])

        # Optional explicit area restriction in the master table.
        allowed_areas = meta.get("allowed_areas") or []
        if allowed_areas and area not in allowed_areas:
            continue

        for bullet in bullets:
            if bullet not in out:
                out.append(bullet)
            if len(out) >= 3:
                return out

    return out[:3]

