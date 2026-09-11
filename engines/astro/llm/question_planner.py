"""Understand a question with the model, then answer it in the reader's voice.

Two passes, both optional:

1. ``plan_question`` asks the model what the reader actually wants and which
   engines to run. It returns ``None`` whenever the model is unavailable, and
   the caller falls back to the older routing.
2. ``write_in_user_voice`` turns the engine output into plain second-person
   prose, with ``enforce_user_voice`` rejecting anything that slips back into
   textbook register.

Nothing here computes astrology. Pass 1 chooses, Python computes, pass 2
phrases.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

_ENG = Path(__file__).resolve().parent.parent
if str(_ENG) not in sys.path:
    sys.path.insert(0, str(_ENG))

from astro_tools import (                                             # noqa: E402
    ASTRO_TOOLS,
    MAX_TOOLS_PER_QUESTION,
    describe_tools,
    evidence_block,
)

VOICE_REPAIR_LIMIT = 1


def _areas() -> list[tuple[str, str]]:
    """Life-area keys with their human titles, straight from the engine."""
    try:
        from confluence_question_engine import DOMAINS_CONFIG
        return [(k, str(v.get("title") or k))
                for k, v in DOMAINS_CONFIG.items() if k != "out_of_domain"]
    except Exception:                                                 # noqa: BLE001
        return [("general_destiny", "Overall life direction")]


def _lang_flavour(lang: str) -> str:
    code = str(lang or "").lower()
    if code in ("hi_en", "hinglish", "hi", "hindi"):
        return ("Write the whole reply in conversational Hindi using English "
                "letters (Hinglish / Roman Hindi). Never use Devanagari "
                "script. Address the reader as 'aap'.")
    if code in ("te_en", "tenglish", "te", "telugu"):
        return ("Write the whole reply in conversational Telugu using English "
                "letters (Tenglish / Roman Telugu). Never use Telugu script. "
                "Address the reader as 'meeru' / 'mee'.")
    return "Write the whole reply in plain, fluent English."


# --------------------------------------------------------------------------
# Pass 1 — understand the question, choose the engines
# --------------------------------------------------------------------------

_PLANNER_SYSTEM = """You are the routing brain of a Vedic astrology service.

A reader has asked a question in their own words. Do not answer it. Decide:

1. restated_intent — what they are actually asking, in one plain sentence.
2. in_scope — true when the question is about a human life: their future,
   work, money, family, health, relationships, children, study, travel,
   property, legal matters, mood, timing, gemstones or remedies. False only
   for questions with nothing to do with a person's life, such as programming,
   general trivia, recipes or device repair. When in doubt, choose true.
3. life_area — the single closest area key from the list below.
4. target_planet — if the reader named a gemstone or a planet, the planet that
   rules it, otherwise empty. Match the intent even when the spelling is
   wrong or informal: emerald / emerland / panna are Mercury, ruby / manik are
   the Sun, pearl / moti are the Moon, red coral / moonga are Mars, yellow
   sapphire / pukhraj are Jupiter, diamond / heera / opal are Venus, blue
   sapphire / neelam are Saturn, hessonite / gomed is Rahu, cat's eye /
   lehsunia is Ketu.
5. tools — up to {max_tools} engines to run, most important first. Always
   include life_area_confluence unless the question is purely about a
   gemstone. Only pass arguments a tool actually declares.

LIFE AREA KEYS
{areas}

AVAILABLE TOOLS
{tools}

Reply with JSON only."""


def plan_question(question: str, *, history: Optional[list[dict]] = None,
                  area_hint: str = "") -> Optional[Any]:
    """Ask the model to interpret the question. ``None`` when it cannot."""
    question = (question or "").strip()
    if not question:
        return None
    try:
        from core.llm_client import complete_model

        from .schemas import QuestionPlan
    except Exception as exc:                                          # noqa: BLE001
        print(f"[planner] import failed: {exc}", flush=True)
        return None

    areas = "\n".join(f"- {k}: {title}" for k, title in _areas())
    system = _PLANNER_SYSTEM.format(max_tools=MAX_TOOLS_PER_QUESTION,
                                    areas=areas, tools=describe_tools())

    recent = ""
    for turn in (history or [])[-4:]:
        body = str(turn.get("content") or "").strip()[:300]
        if body:
            recent += f"{turn.get('role', 'user')}: {body}\n"

    user = ""
    if recent:
        user += f"EARLIER IN THIS CONVERSATION:\n{recent}\n"
    if area_hint:
        user += f"AREA THE READER PICKED FROM A MENU: {area_hint}\n"
    user += f'QUESTION: "{question}"'

    plan = complete_model(QuestionPlan, system, user, temperature=0.1)
    if plan is None:
        return None
    return _sanitise(plan, question)


def _sanitise(plan: Any, question: str) -> Any:
    """Keep only real tools and real area keys.

    A model naming a tool we do not have should lose that one call, not the
    whole plan, so bad entries are dropped rather than raised on.
    """
    valid_areas = {k for k, _ in _areas()}
    if plan.life_area not in valid_areas:
        plan.life_area = "general_destiny"

    from astro_tools import EVENTS, NODE_TOPICS, PLANETS
    planet_by_lower = {p.lower(): p for p in PLANETS}
    plan.target_planet = planet_by_lower.get(
        str(plan.target_planet or "").strip().lower(), "")

    kept = []
    for call in plan.tools:
        tool = ASTRO_TOOLS.get(str(call.tool or "").strip())
        if tool is None:
            continue
        call.tool = tool.name
        if call.args.area and call.args.area not in valid_areas:
            call.args.area = plan.life_area
        if "area" in tool.args and not call.args.area:
            call.args.area = plan.life_area
        call.args.planet = planet_by_lower.get(
            str(call.args.planet or "").strip().lower(), "")
        if "planet" in tool.args and not call.args.planet:
            call.args.planet = plan.target_planet
        if call.args.event and call.args.event.lower() not in EVENTS:
            call.args.event = ""
        if call.args.topic and call.args.topic.lower() not in NODE_TOPICS:
            call.args.topic = ""
        if "event" in tool.args and not call.args.event:
            continue
        if "topic" in tool.args and not call.args.topic:
            continue
        if "planet" in tool.args and not call.args.planet:
            continue
        kept.append(call)

    if not any(c.tool == "life_area_confluence" for c in kept):
        from .schemas import ToolArgs, ToolRequest
        kept.insert(0, ToolRequest(tool="life_area_confluence",
                                   args=ToolArgs(area=plan.life_area,
                                                 planet=plan.target_planet)))
    plan.tools = kept[:MAX_TOOLS_PER_QUESTION]
    if not plan.restated_intent:
        plan.restated_intent = question[:300]
    return plan


def plan_as_calls(plan: Any) -> list[dict]:
    """The plan's tool list in the shape ``run_tools`` expects."""
    calls = []
    for call in getattr(plan, "tools", None) or []:
        args = call.args
        calls.append({
            "tool": call.tool,
            "args": {k: v for k, v in (
                ("area", args.area), ("planet", args.planet),
                ("event", args.event), ("topic", args.topic)) if v},
        })
    return calls


# --------------------------------------------------------------------------
# Pass 2 — write it the way the reader speaks
# --------------------------------------------------------------------------

VOICE_CONTRACT = """You are the reader's own astrologer, talking to them directly.

HOW TO WRITE
- Open with one sentence that answers exactly what they asked, using their own
  framing of it. No preamble, no restating the question back at them.
- Say "you" and "your" throughout. Never write "the native", "the seeker",
  "the querent", "the client", or "this chart indicates" — it is their chart,
  so write "your chart shows".
- A Sanskrit or technical term is allowed only if you explain it in plain
  words in the same sentence: "Saturn's seven-and-a-half-year pressure cycle
  (Sade Sati)" is fine, a bare "Kendradhipati Dosha" or "SAV bindus" is not.
- 150 to 350 words, in three to five short paragraphs. At most two short bold
  lead-ins. No numbered pillar headings, no section scaffolding.
- Be warm and direct. Say the difficult thing plainly when the evidence says
  it, and say what to do about it.

WHAT YOU MAY SAY
- Only what the EVIDENCE below contains. Never name a gemstone, a date, a
  planet or a period that is not in it.
- If the evidence marks a gemstone AVOID, MANTRA_ONLY or STRICTLY_AVOID, never
  suggest wearing it. Explain in plain words why it works against them, then
  give the safe alternative the evidence lists.
- Never contradict the evidence to be encouraging."""

_OUT_OF_SCOPE = """The reader asked something outside astrology. In two or three
warm sentences, say you can't help with that one, name what you can read for
them from their chart, and invite the next question. Say "you", not "the
seeker"."""


def write_in_user_voice(question: str, plan: Any, results: dict[str, Any], *,
                        history: Optional[list[dict]] = None,
                        lang: str = "en") -> str:
    """Second pass. Returns "" when the model is unavailable or unusable."""
    try:
        from confluence_question_engine import _llm_allowed
        if not _llm_allowed("chat"):
            return ""
        from core.config import S
        from openai import OpenAI
    except Exception as exc:                                          # noqa: BLE001
        print(f"[planner] voice import failed: {exc}", flush=True)
        return ""

    in_scope = bool(getattr(plan, "in_scope", True))
    system = (_OUT_OF_SCOPE if not in_scope else VOICE_CONTRACT)
    system += "\n\n" + _lang_flavour(lang)
    if in_scope:
        system += (
            f"\n\nWHAT THEY ARE ASKING\n{getattr(plan, 'restated_intent', '')}"
            f"\n\nEVIDENCE\n{evidence_block(results)}"
        )

    messages: list[dict] = [{"role": "system", "content": system}]
    for turn in (history or [])[-6:]:
        body = str(turn.get("content") or "").strip()
        if body:
            messages.append({"role": turn.get("role", "user"),
                             "content": body[:1000]})
    messages.append({"role": "user", "content": question})

    base = getattr(S, "llm_base_url", "") or "http://host.docker.internal:8000/v1"
    model = getattr(S, "llm_model", "") or "Qwen/Qwen2.5-7B-Instruct-AWQ"
    client = OpenAI(base_url=base.rstrip("/"),
                    api_key=getattr(S, "llm_api_key", "") or "dummy",
                    timeout=120.0)

    from .validate import enforce_user_voice

    for attempt in range(VOICE_REPAIR_LIMIT + 1):
        try:
            resp = client.chat.completions.create(
                model=model, messages=messages, temperature=0.55,
                max_tokens=1400)
        except Exception as exc:                                      # noqa: BLE001
            print(f"[planner] voice call failed: {exc}", flush=True)
            return ""
        choices = getattr(resp, "choices", None) or []
        text = ""
        if choices:
            text = (getattr(choices[0].message, "content", "") or "").strip()
        if not text:
            return ""
        problems = enforce_user_voice(text)
        if not problems or attempt >= VOICE_REPAIR_LIMIT:
            if problems:
                print(f"[planner] voice still off after repair: {problems}",
                      flush=True)
            return text
        messages.append({"role": "assistant", "content": text})
        messages.append({"role": "user", "content": (
            "Rewrite that reply. Problems: " + "; ".join(problems) + ". "
            "Speak to me directly as 'you', and explain any technical term in "
            "plain words in the same sentence. Keep every fact the same.")})
    return ""
