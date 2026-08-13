"""Reject LLM prose that invents facts, dates, planets, or certainty."""

from __future__ import annotations

import re
import json
from typing import Any, Iterable, Optional

from .rules import GENERIC_FACT_IDS, check_prose, check_prose_fields
from .facts import citable_fact_ids, public_fact_payload
from .schemas import QuestionFacts


def _fget(obj: Any, key: str, default: Any = None) -> Any:
    """Read a fact field from a pydantic model or a plain dict.

    Report generation passes the facts model; chat reloads the same facts from
    facts.json, so every grounding gate has to read both shapes or it silently
    passes everything on the chat path.
    """
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _fhas(obj: Any, key: str) -> bool:
    if isinstance(obj, dict):
        return key in obj
    return hasattr(obj, key)


def _walk_strings(obj: Any) -> Iterable[str]:
    if obj is None:
        return
    if isinstance(obj, str):
        yield obj
        return
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_strings(v)
        return
    if isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _walk_strings(v)
        return
    if hasattr(obj, "model_dump"):
        yield from _walk_strings(obj.model_dump())


def _collect_text(obj: Any) -> str:
    return " ".join(_walk_strings(obj))


def _field_pairs(prose: Any) -> list[tuple[str, str]]:
    if prose is None:
        return []
    if hasattr(prose, "model_dump"):
        data = prose.model_dump()
    elif isinstance(prose, dict):
        data = prose
    else:
        return [("text", str(prose))]
    pairs: list[tuple[str, str]] = []
    for k, v in data.items():
        if isinstance(v, str) and v.strip():
            pairs.append((k, v))
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, str) and item.strip():
                    pairs.append((f"{k}[{i}]", item))
                elif isinstance(item, dict):
                    for sk, sv in item.items():
                        if isinstance(sv, str) and sv.strip():
                            pairs.append((f"{k}[{i}].{sk}", sv))
                        elif isinstance(sv, list):
                            for j, x in enumerate(sv):
                                if isinstance(x, str) and x.strip():
                                    pairs.append((f"{k}[{i}].{sk}[{j}]", x))
    return pairs


def validate_slot(
    text: str,
    facts: Any,
    *,
    age_band: str = "",
    area: str = "",
) -> list[str]:
    """Return violations for one prose string (empty = accept)."""
    del age_band  # reserved for future age-stage gates
    return check_prose(text or "", facts, area=area)


def validate_prose_against_facts(prose: Any, facts: Any, *, area: str = "") -> list[str]:
    """Primary QA gate from the correction plan. Empty list = accept."""
    errors: list[str] = []
    text = _collect_text(prose)
    if not text.strip():
        return ["empty_prose"]

    area_hint = area
    if not area_hint and hasattr(prose, "area"):
        area_hint = getattr(prose, "area", "") or ""

    errors.extend(check_prose_fields(_field_pairs(prose), facts, area=area_hint))

    # User-question truth contract: when QuestionFacts came from the full
    # report, the question prose must be grounded in that same canonical
    # promise/activation/timing source. This is a validation invariant, not a
    # prompt instruction.
    if isinstance(facts, QuestionFacts):
        if getattr(facts, "truth_source", "") == "full_report_canonical":
            if getattr(facts, "promise_status", "") != getattr(facts, "canonical_promise_status", ""):
                errors.append("question_canonical_promise_mismatch")
            if getattr(facts, "activation_status", "") != getattr(facts, "canonical_activation_status", ""):
                errors.append("question_canonical_activation_mismatch")
            if getattr(facts, "timing_can_create_promise", False):
                errors.append("question_timing_can_create_promise")

    # Promise / activation consistency for report cards
    cards_facts = _fget(facts, "cards", None)
    if cards_facts is not None and hasattr(prose, "area"):
        fact_by_area = {
            _fget(c, "area", ""): c for c in cards_facts if _fget(c, "area", "")
        }
        cf = fact_by_area.get(getattr(prose, "area", ""))
        if cf is None and getattr(prose, "area", ""):
            # Allow single-card mini facts where cards=[that card]
            if len(list(cards_facts)) == 1:
                cf = cards_facts[0]
            else:
                errors.append(f"unknown_area:{getattr(prose, 'area', '')}")
        if cf is not None:
            status = (_fget(cf, "status", "") or "").lower()
            act = (_fget(cf, "activation_status", "") or "").lower()
            blob = text.lower()
            if status in ("weak", "insufficient_evidence", "mixed"):
                if re.search(
                    r"\b(strongly supported|highly favoured|guaranteed|career success is guaranteed)\b",
                    blob,
                ):
                    errors.append(f"overclaim_status:{getattr(cf, 'area', '')}")
            if act in ("inactive", "weak", "insufficient_evidence"):
                if re.search(
                    r"\b(now is the time|peak window|strongly active now)\b", blob
                ):
                    errors.append(f"overclaim_activation:{getattr(cf, 'area', '')}")

    # Question direction consistency
    if _fhas(facts, "direction") and hasattr(prose, "answer"):
        direction = (_fget(facts, "direction", "") or "").lower()
        answer = (getattr(prose, "answer", "") or "").lower()
        if direction in ("caution", "down") and re.search(
            r"\b(strongly favours|highly supportive|excellent prospects)\b", answer
        ):
            errors.append("question_direction_mismatch")
        if direction in ("support", "up") and re.search(
            r"\b(does not support|unlikely|poor prospects)\b", answer
        ):
            errors.append("question_direction_mismatch")
        if (_fget(facts, "promise_status", "") or "").lower() in (
            "weak",
            "insufficient_evidence",
        ):
            if re.search(r"\b(definitely|guaranteed|will happen)\b", answer):
                errors.append("question_overclaim")

    # Horary: verdict label should remain grounded
    if _fhas(facts, "label") and hasattr(prose, "verdict_line"):
        label = (_fget(facts, "label", "") or "").strip().lower()
        vl = (getattr(prose, "verdict_line", "") or "").lower()
        if label:
            if "yes" in label and not re.search(r"\b(yes|support|favour|favor|lean|open)\b", vl):
                errors.append("horary_label_mismatch")
            elif "no" in label and not re.search(r"\b(no|caution|unlikely|does not favour|does not favor)\b", vl):
                errors.append("horary_label_mismatch")

    # Stronger status grounding. The old gate only rejected words such as
    # "guaranteed", allowing "moderate chance of positive developments" even
    # when the canonical promise was limited/insufficient.
    payload = public_fact_payload(facts) if facts is not None else {}
    if isinstance(payload, dict):
        promise_status = str(payload.get("promise_status") or "").lower()
        if not promise_status and isinstance(payload.get("cards"), list) and hasattr(prose, "area"):
            area = str(getattr(prose, "area", "") or "")
            for card in payload.get("cards") or []:
                if isinstance(card, dict) and str(card.get("area") or "") == area:
                    promise_status = str(card.get("status") or "").lower()
                    break
        if promise_status in ("weak", "insufficient_evidence"):
            if re.search(
                r"\b(moderate chance|good chance|positive developments|strong prospects|"
                r"strong improvement|highly supportive|very favourable|very favorable|"
                r"likely to improve|clear improvement)\b",
                text, re.I,
            ):
                errors.append("weak_promise_positive_escalation")
        elif promise_status == "mixed":
            if re.search(
                r"\b(guaranteed|definitely|certainly|clear improvement|strong prospects)\b",
                text, re.I,
            ):
                errors.append("mixed_promise_escalation")

        # Relationship/parenthood status must never be inferred from a generic
        # area fact.
        if re.search(r"\b(your spouse|your husband|your wife|your children|your child)\b", text, re.I):
            raw = json.dumps(payload, default=str).lower()
            if not any(x in raw for x in ("married", "spouse", "husband", "wife", "existing_child",
                                          "existing children", "parent")):
                errors.append("assumed_relationship_or_parent_status")

    # Palm facts have no dates unless explicitly supplied. Do not let a model
    # manufacture an age window from signal IDs or internal engine metadata.
    if isinstance(payload, dict) and payload.get("kind") == "palm":
        if re.search(r"\b(?:age|aged)\s+\d{1,3}\b", text, re.I):
            allowed = " ".join(str(x) for x in (payload.get("future_windows") or []))
            if not re.search(r"\b\d{1,3}\b", allowed):
                errors.append("palm_unvalidated_age")

    # Deduplicate while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for e in errors:
        if e not in seen:
            seen.add(e)
            out.append(e)
    return out


_OPPORTUNITY_LANGUAGE = re.compile(
    r"\b(genuine (?:opportunity|opening)|opportunity window|real potential|"
    r"actively supporting|strong support(?:ive)? window|favourable window)\b",
    re.I,
)


def validate_conversational_area(field: str, text: str, card: Any) -> list[str]:
    """Area-level tone contract on top of the shared prose rules.

    A card the engine classifies as a challenge is something to look after.
    Describing it as an opportunity window reads as the opposite advice.
    """
    if field != "outlook" or not (text or "").strip():
        return []
    kind = str(getattr(card, "kind", "") or "").lower()
    if kind == "challenge" and _OPPORTUNITY_LANGUAGE.search(text):
        return ["challenge_framed_as_opportunity"]
    return []


_HEDGE = re.compile(
    r"\b(?:may|might|could|can|if|tends?|often|usually|perhaps|likely)\b", re.I,
)
_STOP_WORDS = frozenset({
    "and", "the", "your", "you", "life", "amp", "for",
})


def validate_mind_now_line(text: str, facts: Any) -> list[str]:
    """Keep the "what may be on your mind" block honest.

    Two failures matter here. Naming a subject the reading never flagged turns
    the block into cold reading, and stating any of it flatly turns a
    possibility into a claim about a life we cannot see.

    Astrology grounds the block in ``life_state`` and palmistry in
    ``palm_state``; the honesty requirement is identical, so one gate serves
    both rather than drifting apart in two copies.
    """
    t = (text or "").strip()
    if not t:
        return []
    state = _fget(facts, "life_state") or _fget(facts, "palm_state") or {}
    topics = _fget(state, "mind_now") or []
    if not topics:
        return ["mind_now_without_facts"]

    allowed: set[str] = set()
    for topic in topics:
        for source in (_fget(topic, "area") or "", _fget(topic, "label") or ""):
            for word in re.findall(r"[a-z]{3,}", str(source).lower()):
                if word not in _STOP_WORDS:
                    allowed.add(word)
        for phrase in _fget(topic, "experience") or []:
            for word in re.findall(r"[a-z]{4,}", str(phrase).lower()):
                if word not in _STOP_WORDS:
                    allowed.add(word)

    words = {w for w in re.findall(r"[a-z]{3,}", t.lower())}
    errors: list[str] = []
    if allowed and not (words & allowed):
        errors.append("mind_now_topic_not_in_facts")
    if not _HEDGE.search(t):
        errors.append("mind_now_stated_as_fact")
    return errors


def mind_now_topic_index(text: str, facts: Any) -> Optional[int]:
    """Which flagged topic a line is talking about, or None if unclear.

    The engine picks the topics for this block deliberately, holding a place
    for an area that is going well so it does not read as a list of warnings.
    A model handed three experience phrases will happily spend all three lines
    on the first topic, which quietly undoes that, so the screening step needs
    to know which topic each line landed on.
    """
    state = _fget(facts, "life_state") or _fget(facts, "palm_state") or {}
    topics = list(_fget(state, "mind_now") or [])
    words = {w for w in re.findall(r"[a-z]{4,}", (text or "").lower())} - _STOP_WORDS
    if not topics or not words:
        return None
    best: Optional[int] = None
    best_score = 0
    for i, topic in enumerate(topics):
        vocab: set[str] = set()
        sources = [str(_fget(topic, "label") or ""), str(_fget(topic, "area") or "")]
        sources += [str(x) for x in (_fget(topic, "experience") or [])]
        for source in sources:
            vocab |= {w for w in re.findall(r"[a-z]{4,}", source.lower())}
        score = len(words & (vocab - _STOP_WORDS))
        if score > best_score:
            best, best_score = i, score
    return best


_RELATION_WORDS = {
    "father": ("father", "dad", "paternal"),
    "mother": ("mother", "mum", "maternal"),
    "siblings": ("sibling", "brother", "sister", "elder", "eldest", "youngest",
                 "last-born", "birth order"),
    "home": ("home", "household", "domestic", "childhood", "upbringing",
             "roof", "family life"),
}
# Nothing about a relative is a prediction. The engines describe who they were
# to grow up around; anything about their future, their body or their money is
# the model filling a silence.
_FAMILY_FORECAST = re.compile(
    r"\b(?:will|shall|going to|about to|soon|in the coming|next year|"
    r"pass(?:es|ed|ing)? away|die|death|illness|ill health|hospital|"
    r"surgery|inherit(?:ance)?|estate|will leave you)\b", re.I,
)
# A leaning stated as a leaning. One method saw it, so the sentence has to
# carry that somewhere — either a hedge or an attribution to the reading.
_SOFT_ATTRIBUTION = re.compile(
    r"\b(?:reads? as|comes? across|seems?|appears?|sounds? like|"
    r"the picture is|suggests?|leans?|one method'?s? reading|"
    r"rather than a settled fact)\b", re.I,
)


def _family_relation(text: str) -> Optional[str]:
    """Which relative a background line is about, by the words it uses."""
    low = (text or "").lower()
    for relation, words in _RELATION_WORDS.items():
        if any(w in low for w in words):
            return relation
    return None


def validate_family_line(text: str, facts: Any) -> list[str]:
    """Keep the background block tied to the relative the engines described.

    Three ways this block goes wrong, and all three are worse here than
    anywhere else on the page because a reader checks these lines against
    people they actually know: naming a relative the methods said nothing
    about, moving the mother's description onto the father, and turning a
    single method's leaning into a settled statement.
    """
    t = (text or "").strip()
    if not t:
        return []
    notes = _fget(facts, "family_notes") or []
    if not notes:
        return ["family_note_without_facts"]

    by_relation = {str(_fget(n, "relation") or ""): n for n in notes}
    relation = _family_relation(t)
    errors: list[str] = []
    if relation is None:
        return ["family_note_names_no_relation"]
    note = by_relation.get(relation)
    if note is None:
        return ["family_note_relation_not_in_facts"]

    vocab: set[str] = set()
    for source in list(_fget(note, "notes") or []) + list(_fget(note, "tags") or []):
        vocab |= {w for w in re.findall(r"[a-z]{4,}", str(source).lower())}
    # The relation noun is in the source sentence too, so leaving it in the
    # shared vocabulary would let "your mother travelled constantly" match on
    # the word "mother" alone — the overlap has to be about the description.
    ignore = _STOP_WORDS | {
        w for words in _RELATION_WORDS.values() for w in words if len(w) >= 4
    }
    vocab -= ignore
    words = {w for w in re.findall(r"[a-z]{4,}", t.lower())} - ignore
    if vocab and not (words & vocab):
        errors.append("family_note_detail_not_in_facts")
    try:
        methods = int(_fget(note, "method_count") or 0)
    except (TypeError, ValueError):
        methods = 0
    if methods <= 1 and not _HEDGE.search(t) and not _SOFT_ATTRIBUTION.search(t):
        errors.append("family_note_single_method_stated_flatly")
    if _FAMILY_FORECAST.search(t):
        errors.append("family_note_predicts")
    return errors


_RECITED_FIELDS = re.compile(
    r"\b(?:emotional|decision) pressure\b|\bactivation(?: status)?\b|"
    r"\bchapter tone\b|\blikelihood\b|\blife state\b|\bpressure is (?:low|high|"
    r"moderate|very high)\b|\b(?:low|high|moderate) (?:pressure|activation)\b",
    re.I,
)


def validate_why_now(text: str) -> list[str]:
    """The "why now" paragraph must describe the feeling, not the fields.

    Handed banded levels, a model will happily write "the emotional pressure is
    low but the decision pressure is high", which is our schema read aloud. It
    is also the one part of the page a reader would quote back as proof that a
    machine wrote it.
    """
    if not (text or "").strip():
        return []
    return ["why_now_recites_fact_fields"] if _RECITED_FIELDS.search(text) else []


_HAND_CHANGE_CLAIM = re.compile(
    r"\b(?:grown into|developed|changed|becoming|become|stronger now|"
    r"used to be|no longer|left behind|outgrown)\b", re.I,
)
_HAND_AGREEMENT_CLAIM = re.compile(
    r"\b(?:both hands|either hand|agree|much the same|consistent across|"
    r"same on both)\b", re.I,
)
# Life-area names. The two-hand comparison is made of line themes and traits;
# an aspect key appearing here means the model reached into the life-area cards
# and attached them to a hand, which the comparison never said.
_PALM_AREA_WORDS = re.compile(
    r"\b(?:character|temperament|mind|intellect|love|relationships?|career|"
    r"wealth|money|health|vitality|travel|fortune)\b", re.I,
)


def validate_hand_contrast_note(text: str, facts: Any) -> list[str]:
    """The two-hand story must come from the two-hand comparison.

    "Your dominant hand shows how much you have grown" is the most persuasive
    sentence on a palm page, which is exactly why it cannot be written when the
    comparison found no difference — or when only one hand was photographed and
    there is no comparison at all.
    """
    t = (text or "").strip()
    if not t:
        return []
    contrast = _fget(facts, "hand_contrast") or {}
    steady = list(_fget(contrast, "steady") or [])
    developed = list(_fget(contrast, "developed") or [])
    latent = list(_fget(contrast, "latent") or [])
    traits = list(_fget(contrast, "developed_traits") or []) + list(
        _fget(contrast, "latent_traits") or [])
    if not (steady or developed or latent or traits):
        return ["hand_contrast_without_facts"]

    errors: list[str] = []
    if _HAND_CHANGE_CLAIM.search(t) and not (developed or latent or traits):
        # Both hands agreeing everywhere is a real finding — it says these
        # traits are long-standing — but it is the opposite of a change.
        errors.append("hand_contrast_change_not_in_facts")

    shared = _phrase_words(steady)
    one_sided = _phrase_words(developed + latent + traits) - shared
    allowed = shared | one_sided
    words = {w for w in re.findall(r"[a-z]{4,}", t.lower())}
    if allowed and not (words & allowed):
        errors.append("hand_contrast_theme_not_in_facts")

    errors += _hand_attribution_errors(t, contrast)

    area_words = {m.group(0).lower() for m in _PALM_AREA_WORDS.finditer(t)}
    if len(area_words - allowed) >= 2:
        errors.append("hand_contrast_uses_life_areas")
    return errors


def _phrase_words(phrases: Iterable[str]) -> set[str]:
    out: set[str] = set()
    for phrase in phrases:
        for word in re.findall(r"[a-z]{4,}", str(phrase).lower()):
            if word not in _STOP_WORDS:
                out.add(word)
    return out


def _hand_attribution_errors(text: str, contrast: Any) -> list[str]:
    """Each hand may only be credited with what that hand actually showed.

    The comparison is the one part of a palm reading a reader can check against
    their own life, so getting it backwards — crediting the lived hand with a
    need the underlying one carries, or calling a one-sided trait shared — does
    more damage than saying nothing.
    """
    t = (text or "").strip()
    if not t or contrast is None:
        return []
    shared = _phrase_words(_fget(contrast, "steady") or [])
    dominant_only = _phrase_words(
        list(_fget(contrast, "developed") or [])
        + list(_fget(contrast, "developed_traits") or [])) - shared
    other_only = _phrase_words(
        list(_fget(contrast, "latent") or [])
        + list(_fget(contrast, "latent_traits") or [])) - shared
    if not (dominant_only or other_only):
        return []

    dominant = str(_fget(contrast, "dominant_hand") or "right").lower()
    other = "left" if dominant == "right" else "right"
    names_dominant = re.compile(rf"\b(?:{dominant}|dominant|lived|active)\s+hand\b", re.I)
    names_other = re.compile(
        rf"\b(?:{other}|non-?dominant|other|underlying|inner)\s+hand\b", re.I)

    # Clauses, not sentences: "your right hand shows X, while your left hand
    # shows Y" is one sentence naming both hands, and a whole-sentence check
    # cannot tell which half is wrong.
    for sentence in re.split(r"(?<=[.!?])\s+|\s*[;—]\s*|,?\s+(?:while|whereas|but|however)\s+",
                             t, flags=re.I):
        said = {w for w in re.findall(r"[a-z]{4,}", sentence.lower())}
        if _HAND_AGREEMENT_CLAIM.search(sentence) and (said & (dominant_only | other_only)):
            return ["hand_contrast_agreement_misstated"]
        for names, own, theirs in (
            (names_dominant, dominant_only, other_only),
            (names_other, other_only, dominant_only),
        ):
            if names.search(sentence) and (said & theirs) and not (said & own):
                return ["hand_contrast_attribution_swapped"]
    return []


def validate_card_prose(
    prose: Any,
    facts: Any,
    *,
    age_band: str = "",
) -> list[str]:
    del age_band
    return validate_prose_against_facts(prose, facts, area=getattr(prose, "area", ""))


def validate_question_prose(prose: Any, facts: Any) -> list[str]:
    return validate_prose_against_facts(prose, facts)


def validate_horary_prose(prose: Any, facts: Any) -> list[str]:
    return validate_prose_against_facts(prose, facts)


def validate_palm_prose(prose: Any, facts: Any) -> list[str]:
    return validate_prose_against_facts(prose, facts)


_CHAT_POSITIVE_ESCALATION = re.compile(
    r"\b(strongly supported|strongly favours|strongly favors|highly favourable|"
    r"highly favorable|excellent prospects|very likely|will definitely|"
    r"guaranteed|assured|certain to|clear improvement|strong prospects)\b",
    re.I,
)
_CHAT_NEGATIVE_ESCALATION = re.compile(
    r"\b(will fail|no chance|impossible|never happen|doomed)\b", re.I,
)


def _chat_area_grounding(text: str, facts: Any) -> list[str]:
    """Hold a chat answer to the same promise grounding as report prose.

    ``validate_prose_against_facts`` only runs its status gates when the prose
    object names an area. A ChatAnswer never does, so an answer about a
    weakly-promised area used to skip the check that report cards must pass.
    """
    errors: list[str] = []
    blob = (text or "").lower()
    if not blob.strip():
        return errors
    for card in list(_fget(facts, "cards", None) or []):
        area = str(_fget(card, "area", "") or "")
        label = str(_fget(card, "label", "") or "")
        names = [n.lower() for n in (area.replace("_", " "), label) if n]
        if not any(n and n in blob for n in names):
            continue
        status = str(_fget(card, "status", "") or "").lower()
        direction = str(_fget(card, "direction", "") or "").lower()
        if status in ("weak", "insufficient_evidence", "mixed"):
            if _CHAT_POSITIVE_ESCALATION.search(blob):
                errors.append(f"chat_overclaim_status:{area}")
        if direction in ("up", "support") and _CHAT_NEGATIVE_ESCALATION.search(blob):
            errors.append(f"chat_underclaim_direction:{area}")
    return errors


_YES_LABEL = re.compile(r"\byes\b|\bfavour|\bfavor|\bsupport", re.I)
_NO_LABEL = re.compile(r"\bno\b|\bnot\b|\bunlikely\b|\bagainst\b|\bunfavour|\bunfavor", re.I)
# Only assertive phrasing counts as reversing a verdict. A bare "yes" or "no"
# appears in perfectly grounded answers ("there is no fixed date"), and gating
# on those refuses fair questions.
_CHAT_ASSERTS_YES = re.compile(
    r"(?:^|[.!?]\s+)yes\b|\bthe answer is yes\b|\bit will happen\b|"
    r"\bthis will happen\b|\byou will get it\b",
    re.I,
)
_CHAT_ASSERTS_NO = re.compile(
    r"(?:^|[.!?]\s+)no[,.]|\bthe answer is no\b|\bit will not happen\b|"
    r"\bthis will not happen\b|\byou will not get it\b",
    re.I,
)


def _chat_horary_grounding(text: str, facts: Any) -> list[str]:
    """A horary follow-up may explain the verdict — never reverse it.

    The verdict is computed by the horary engine and printed in the report, so
    an answer that swings the other way contradicts the page it sits under.
    """
    if str(_fget(facts, "kind", "") or "") != "horary":
        return []
    blob = (text or "").lower()
    if not blob.strip():
        return []
    errors: list[str] = []
    label = str(_fget(facts, "label", "") or "")
    favourable = bool(_fget(facts, "favourable", False))
    contradicted = bool(_fget(facts, "contradicted", False))

    says_no = bool(_NO_LABEL.search(label))
    says_yes = bool(_YES_LABEL.search(label)) and not says_no
    if not label:
        says_yes, says_no = favourable, not favourable

    if says_no:
        if _CHAT_POSITIVE_ESCALATION.search(blob) or _CHAT_ASSERTS_YES.search(blob):
            errors.append("chat_horary_verdict_flip")
    if says_yes:
        if _CHAT_NEGATIVE_ESCALATION.search(blob) or _CHAT_ASSERTS_NO.search(blob):
            errors.append("chat_horary_verdict_flip")
    # When the methods disagreed the report is deliberately cautious; chat must
    # not resolve that disagreement into a confident answer either way.
    if contradicted and (_CHAT_POSITIVE_ESCALATION.search(blob)
                         or _CHAT_NEGATIVE_ESCALATION.search(blob)):
        errors.append("chat_horary_certainty_on_contradicted")
    return errors


def _chat_palm_grounding(text: str, facts: Any) -> list[str]:
    """Hold a palm follow-up to the strength the reading actually assigned."""
    if str(_fget(facts, "kind", "") or "") != "palm":
        return []
    blob = (text or "").lower()
    if not blob.strip():
        return []
    errors: list[str] = []
    for aspect in list(_fget(facts, "aspects", None) or []):
        key = str(_fget(aspect, "aspect", "") or "")
        title = str(_fget(aspect, "title", "") or "")
        names = [n.lower() for n in (key.replace("_", " "), title) if n]
        if not any(n and n in blob for n in names):
            continue
        direction = str(_fget(aspect, "direction", "") or "").lower()
        strength = str(_fget(aspect, "strength", "") or "").lower()
        if direction in ("caution", "down", "mixed") or strength in ("tentative", "weak"):
            if _CHAT_POSITIVE_ESCALATION.search(blob):
                errors.append(f"chat_palm_overclaim:{key}")
        if direction in ("support", "up") and _CHAT_NEGATIVE_ESCALATION.search(blob):
            errors.append(f"chat_palm_underclaim:{key}")

    # The line-timing engine says when a theme reads most strongly, never that
    # an outcome lands then. "You will be rich between 27 and 36" is the answer
    # this reading must never give, however the question is phrased.
    if _AGE_MENTION.search(blob) and _OUTCOME_PROMISE.search(blob):
        errors.append("chat_palm_age_outcome")

    errors += _hand_attribution_errors(text, _fget(facts, "hand_contrast"))
    return errors


_AGE_MENTION = re.compile(
    r"\bages?\s+\d{1,3}\b|\bbetween the ages of\b|\bage of\s+\d{1,3}\b|"
    r"\baged\s+\d{1,3}\b|\bby\s+\d{2}\b", re.I,
)
_OUTCOME_PROMISE = re.compile(
    r"\b(?:will (?:become|be|happen|occur|come|get|marry|bring)|"
    r"is likely to (?:occur|happen|come|be)|likely to occur|you will|you'll|"
    r"expected to|set to|is going to)\b", re.I,
)


def validate_chat_answer(prose: Any, facts: Any) -> list[str]:
    if getattr(prose, "out_of_scope", False):
        return []
    errors = validate_prose_against_facts(prose, facts)
    answer = getattr(prose, "answer", "") or ""
    errors.extend(_chat_area_grounding(answer, facts))
    errors.extend(_chat_horary_grounding(answer, facts))
    errors.extend(_chat_palm_grounding(answer, facts))
    used = list(getattr(prose, "used_fact_ids", None) or [])
    if not used:
        errors.append("chat_missing_used_fact_ids")
    else:
        allowed_ids = set(GENERIC_FACT_IDS) | citable_fact_ids(facts)
        for fid in used:
            if str(fid) not in allowed_ids:
                errors.append(f"chat_unknown_fact_id:{fid}")
                break
    return list(dict.fromkeys(errors))


# Back-compat alias
def validate_overlay(prose: Any, facts: Any) -> list[str]:
    return validate_prose_against_facts(prose, facts)
