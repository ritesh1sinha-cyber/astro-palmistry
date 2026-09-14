"""Deterministic astrology tools the model may call to answer a question.

The model never computes astrology. It reads ``describe_tools()``, names the
tools it wants, and ``run_tools`` executes the real engine functions. Every
entry here wraps code that already exists elsewhere in ``engines/astro`` — this
module adds no astrological reasoning of its own, only argument marshalling and
JSON-safe serialisation.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

MAX_TOOLS_PER_QUESTION = 4

PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
           "Rahu", "Ketu")

EVENTS = ("marriage", "child", "career", "property", "education", "travel",
          "business", "recovery", "wealth", "status")

NODE_TOPICS = ("progeny", "medical", "yogas")


@dataclass
class AstroTool:
    """One callable the planner may choose.

    ``description`` is the only thing the model sees, so it is written in the
    words a reader would use, not in the words the engine uses.
    """
    name: str
    description: str
    fn: Callable[..., Any]
    args: dict[str, str] = field(default_factory=dict)


# --------------------------------------------------------------------------
# JSON-safe serialisation
# --------------------------------------------------------------------------

def jsonable(value: Any, _depth: int = 0) -> Any:
    """Flatten dataclasses, dates and nested containers for the prompt."""
    if _depth > 6:
        return str(value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return jsonable(dataclasses.asdict(value), _depth + 1)
    if isinstance(value, dict):
        return {str(k): jsonable(v, _depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [jsonable(v, _depth + 1) for v in value]
    for attr in ("model_dump", "_asdict"):
        if hasattr(value, attr):
            try:
                return jsonable(getattr(value, attr)(), _depth + 1)
            except Exception:                                         # noqa: BLE001
                break
    if hasattr(value, "__dict__"):
        return jsonable(vars(value), _depth + 1)
    return str(value)


def _birth_year(pc: dict) -> int:
    dob = str((pc.get("meta") or {}).get("dob") or "")
    for chunk in dob.replace("/", "-").split("-"):
        if len(chunk) == 4 and chunk.isdigit():
            return int(chunk)
    return date.today().year - 30


def _is_female(pc: dict) -> bool:
    try:
        from chart_client import female_from_pc
        return bool(female_from_pc(pc))
    except Exception:                                                 # noqa: BLE001
        return str((pc.get("meta") or {}).get("gender", "")).lower().startswith("f")


# --------------------------------------------------------------------------
# Tool bodies — each returns a plain dict
# --------------------------------------------------------------------------

def _t_life_area_confluence(pc: dict, *, area: str = "", question: str = "",
                            planet: str = "", **_: Any) -> Any:
    from confluence_question_engine import analyze_question_confluence
    return analyze_question_confluence(pc, question, domain_override=area,
                                       target_planet=planet)


def _t_gemstone_audit(pc: dict, **_: Any) -> Any:
    from confluence_question_engine import audit_chart_gemstones
    return audit_chart_gemstones(pc)


def _t_gemstone_for_planet(pc: dict, *, planet: str = "", **_: Any) -> Any:
    from confluence_question_engine import audit_chart_gemstones
    full = audit_chart_gemstones(pc)
    audit = full.get("audit") or {}
    if planet not in audit:
        return full
    return {
        "lagna": full.get("lagna"),
        "lagna_lord": full.get("lagna_lord"),
        "planet": planet,
        **audit[planet],
        "recommended_alternatives": [
            {"planet": p, "gem": inf.get("gem")}
            for p, inf in audit.items() if inf.get("status") == "RECOMMENDED"
        ],
    }


def _t_event_promise(pc: dict, *, event: str = "", **_: Any) -> Any:
    import future_event_timing as fet
    fn = getattr(fet, f"assess_{event}_promise", None)
    if fn is None:
        raise ValueError(f"no promise assessor for event {event!r}")
    if event == "marriage":
        return fn(pc, female=_is_female(pc))
    return fn(pc)


def _t_area_promise(pc: dict, *, area: str = "", **_: Any) -> Any:
    from personalized_confluence import resolve_promise
    return resolve_promise(pc, area)


def _t_timing_windows(pc: dict, *, question: str = "", **_: Any) -> Any:
    from question_answer import answer as qa_answer
    return qa_answer(pc, question)


def _t_dasha_windows(pc: dict, **_: Any) -> Any:
    from classical_timing import horizon_buckets
    return horizon_buckets(pc)


def _t_dasha_at_date(pc: dict, **_: Any) -> Any:
    from report_confluence import dasha_confluence
    return dasha_confluence(pc)


def _t_eventful_years(pc: dict, **_: Any) -> Any:
    from gk_transit_dasha import upcoming_eventful_years
    return upcoming_eventful_years(pc, _birth_year(pc))


def _t_live_transits(pc: dict, **_: Any) -> Any:
    from transit_planet_analysis import analyze_transit_planet
    res = analyze_transit_planet(pc)
    if isinstance(res, dict):
        # The card list carries the whole paid render; the headline fields are
        # what a chat answer can actually use.
        return {k: v for k, v in res.items() if k != "cards"}
    return res


def _t_mind_and_transits(pc: dict, **_: Any) -> Any:
    """Chandra Naadi Parts 1+2 (incl. Badhaka, Punarpoo, Manthi, modulation)."""
    from specialist_readings import build_specialist_readings

    gender = "female" if str((pc.get("meta") or {}).get("gender", "")).lower().startswith("f") else "male"
    bundle = build_specialist_readings(pc, gender=gender)
    block = bundle.get("chandra_naadi") or {}
    # Keep a compact Moon-pressure note from the lighter helper when available.
    thin: dict[str, Any] = {}
    try:
        from confluence_question_engine import analyze_chandra_nadi
        thin = analyze_chandra_nadi(pc) or {}
    except Exception:  # noqa: BLE001
        thin = {}
    return {
        "status": block.get("status", "unavailable"),
        "findings": block.get("findings") or [],
        "moon_summary": thin.get("moon_summary", ""),
        "conjunctions": thin.get("conjunctions") or [],
        "aspects": thin.get("aspects") or [],
        "transit_hits": thin.get("transit_hits") or [],
        "source": "chandra_naadi_vol1_vol2",
    }


def _t_lal_kitab(pc: dict, **_: Any) -> Any:
    """Lal Kitab diagnostics, upayas and precautions for this chart."""
    from specialist_readings import build_specialist_readings

    gender = "female" if str((pc.get("meta") or {}).get("gender", "")).lower().startswith("f") else "male"
    bundle = build_specialist_readings(pc, gender=gender)
    block = bundle.get("lal_kitab") or {}
    return {
        "status": block.get("status", "unavailable"),
        "findings": block.get("findings") or [],
        "precautions": block.get("precautions") or [],
        "source": "lal_kitab",
    }


def _t_chart_strength(pc: dict, **_: Any) -> Any:
    from confluence_question_engine import compute_chart_ashtakavarga
    return compute_chart_ashtakavarga(pc)


def _t_structural_audit(pc: dict, **_: Any) -> Any:
    from confluence_question_engine import audit_gate0_hardware
    return audit_gate0_hardware(pc)


def _t_nodes_analysis(pc: dict, *, topic: str = "", **_: Any) -> Any:
    import rahu_ketu_analysis as rk
    fn = getattr(rk, f"analyze_{topic}", None)
    if fn is None:
        raise ValueError(f"no nodal analyser for topic {topic!r}")
    return fn(pc)


def _t_planet_condition(pc: dict, *, planet: str = "", **_: Any) -> Any:
    from period_planet_status import planet_role, planet_strength
    strength = planet_strength(pc, planet)
    return {"planet": planet, "strength": strength,
            "role": planet_role(pc, planet)}


def _t_longevity_context(pc: dict, **_: Any) -> Any:
    from confluence_longevity_lane import build_longevity_context
    return build_longevity_context(pc)


def _t_remedies(pc: dict, *, area: str = "", question: str = "",
                lang: str = "en", **_: Any) -> Any:
    from remedy_block import build as build_remedy
    return build_remedy(pc, domain=area, question=question, lang=lang)


ASTRO_TOOLS: dict[str, AstroTool] = {
    t.name: t for t in (
        AstroTool(
            "life_area_confluence",
            "Full multi-layer reading of one life area: the ruling house and "
            "its lord, supporting houses, natural significators, divisional "
            "cross-checks, current period and remedies. The general-purpose "
            "tool — use it for almost every life question.",
            _t_life_area_confluence,
            {"area": "one of the life area keys"},
        ),
        AstroTool(
            "gemstone_audit",
            "Safety verdict for all nine gemstones against this chart "
            "(recommended, avoid, or mantra only). Use when someone asks "
            "which stone suits them, without naming one.",
            _t_gemstone_audit,
        ),
        AstroTool(
            "gemstone_for_planet",
            "Safety verdict for ONE gemstone, plus the safe alternatives. Use "
            "when someone names a specific stone or its ruling planet, however "
            "they spell it, and asks whether they can wear it or why not.",
            _t_gemstone_for_planet,
            {"planet": f"one of {', '.join(PLANETS)}"},
        ),
        AstroTool(
            "event_promise",
            "Whether the chart actually promises a specific life event at all, "
            "with the supporting and denying factors. Use for 'will I ever...' "
            "and 'is it possible that...' questions.",
            _t_event_promise,
            {"event": f"one of {', '.join(EVENTS)}"},
        ),
        AstroTool(
            "area_promise",
            "The canonical natal promise for one life area — the same verdict "
            "the paid report used, so the answer cannot contradict it.",
            _t_area_promise,
            {"area": "one of the life area keys"},
        ),
        AstroTool(
            "timing_windows",
            "Dated windows over the next few years when the matter asked about "
            "is most likely to move. Use when the question is 'when'.",
            _t_timing_windows,
        ),
        AstroTool(
            "dasha_windows",
            "Near, middle and far horizon buckets of the running planetary "
            "periods. Use for broad 'what is coming' questions.",
            _t_dasha_windows,
        ),
        AstroTool(
            "dasha_at_date",
            "Every period system agreeing or disagreeing right now "
            "(Vimshottari, Yogini, Chara). Use when the question is about the "
            "present phase.",
            _t_dasha_at_date,
        ),
        AstroTool(
            "eventful_years",
            "The next few calendar years flagged as eventful for this chart.",
            _t_eventful_years,
        ),
        AstroTool(
            "live_transits",
            "Where the planets are moving right now against this chart, with "
            "the period overlay.",
            _t_live_transits,
        ),
        AstroTool(
            "mind_and_transits",
            "Emotional and mental state from Chandra Naadi (Parts 1 and 2): "
            "Moon placement, Badhaka obstacles, Punarpoo delays, Manthi, "
            "Chandrashtama and current transit pressure. Use for stress, "
            "anxiety, confidence, motivation, sleep, and obstacle questions.",
            _t_mind_and_transits,
        ),
        AstroTool(
            "lal_kitab",
            "Lal Kitab house/planet diagnostics with practical upayas "
            "(remedies) and precautions (parhez). Use when the reader asks "
            "for Lal Kitab remedies, sleeping planets, ancestral debt, "
            "Takkar/Dhoka friction, or what to give in charity.",
            _t_lal_kitab,
        ),
        AstroTool(
            "chart_strength",
            "Numeric benefic-point strength of every sign and house.",
            _t_chart_strength,
        ),
        AstroTool(
            "structural_audit",
            "Screening for severe structural difficulties in the chart that "
            "should temper any optimistic verdict, especially around "
            "employability and early childhood development.",
            _t_structural_audit,
        ),
        AstroTool(
            "nodes_analysis",
            "What Rahu and Ketu say about one theme.",
            _t_nodes_analysis,
            {"topic": f"one of {', '.join(NODE_TOPICS)}"},
        ),
        AstroTool(
            "planet_condition",
            "How strong one planet is in this chart and whether it helps or "
            "harms the person. Use when a specific planet is named.",
            _t_planet_condition,
            {"planet": f"one of {', '.join(PLANETS)}"},
        ),
        AstroTool(
            "longevity_context",
            "Longevity and vulnerable-period markers. Use only for direct "
            "questions about lifespan or serious health risk.",
            _t_longevity_context,
        ),
        AstroTool(
            "remedies",
            "Practical and devotional remedies for one life area.",
            _t_remedies,
            {"area": "one of the life area keys"},
        ),
    )
}


def describe_tools() -> str:
    """The tool menu exactly as the planner model sees it."""
    lines = []
    for tool in ASTRO_TOOLS.values():
        arg_txt = ""
        if tool.args:
            arg_txt = "  args: " + "; ".join(
                f"{k} ({v})" for k, v in tool.args.items())
        lines.append(f"- {tool.name}: {tool.description}{arg_txt}")
    return "\n".join(lines)


ALWAYS_ON_PROBLEM_TOOLS = ("mind_and_transits", "lal_kitab", "structural_audit")


def always_on_problem_evidence(pc: dict, *, question: str = "",
                               lang: str = "en") -> dict[str, Any]:
    """Chandra Naadi + Lal Kitab + Gate-0 judgement for every life problem.

    These sit outside the planner's 4-tool cap so a career/marriage/health
    question still gets all three lenses even when the model never names them.
    """
    results: dict[str, Any] = {}
    kwargs = {"question": question, "lang": lang}
    for name in ALWAYS_ON_PROBLEM_TOOLS:
        tool = ASTRO_TOOLS.get(name)
        if tool is None:
            continue
        try:
            results[name] = jsonable(tool.fn(pc, **kwargs))
        except Exception as exc:                                      # noqa: BLE001
            print(f"[astro_tools] always-on {name} failed: "
                  f"{type(exc).__name__}: {exc}", flush=True)
    return results


def run_tools(pc: dict, calls: list[dict], *, question: str = "",
              lang: str = "en") -> dict[str, Any]:
    """Execute the planner's chosen tools.

    Unknown names are dropped rather than raising: a model that invents a tool
    should cost us one missing evidence block, not the whole answer.
    Chandra Naadi, Lal Kitab and the structural chart audit are then merged
    in so every in-scope problem is judged on those lenses.
    """
    results: dict[str, Any] = {}
    for call in (calls or [])[:MAX_TOOLS_PER_QUESTION]:
        name = str((call or {}).get("tool") or "").strip()
        tool = ASTRO_TOOLS.get(name)
        if tool is None or name in results:
            continue
        kwargs = dict((call or {}).get("args") or {})
        kwargs.setdefault("question", question)
        kwargs.setdefault("lang", lang)
        try:
            results[name] = jsonable(tool.fn(pc, **kwargs))
        except Exception as exc:                                      # noqa: BLE001
            print(f"[astro_tools] {name} failed: {type(exc).__name__}: {exc}",
                  flush=True)
    for name, payload in always_on_problem_evidence(
            pc, question=question, lang=lang).items():
        results.setdefault(name, payload)
    return results


def evidence_block(results: dict[str, Any], *, limit: int = 2600) -> str:
    """Render tool output for the prompt, one labelled section per tool."""
    import json

    chunks = []
    for name, payload in results.items():
        try:
            body = json.dumps(payload, ensure_ascii=False, indent=1,
                              default=str)
        except Exception:                                             # noqa: BLE001
            body = str(payload)
        if len(body) > limit:
            body = body[:limit] + "\n… (truncated)"
        chunks.append(f"[{name.upper()}]\n{body}")
    return "\n\n".join(chunks) if chunks else "(no tool output available)"
