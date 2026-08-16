"""Regenerate life_state + palm_state HTML from current fallback (no PyJHora)."""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT),
    str(ROOT / "engines" / "astro"),
    str(ROOT / "engines"),
    str(ROOT / "core"),
]

from llm.fallback import conversational_fallback, conversational_palm_fallback
from llm.life_state import build_life_state
from llm.schemas import PalmFacts, ReportFacts, VedicContext
import palm_conversational as PC
import report_conversational as RC


TODAY = date(2026, 8, 13)
REVIEW = ROOT / "ci-storage" / "review_html"


def _keep_fields(model, data):
    if not isinstance(data, dict):
        return data
    fields = getattr(model, "model_fields", {})
    out = {}
    for key, finfo in fields.items():
        if key not in data:
            continue
        val = data[key]
        ann = finfo.annotation
        origin = getattr(ann, "__origin__", None)
        args = getattr(ann, "__args__", ())
        inner = None
        if origin is list and args:
            inner = args[0]
        if inner is not None and hasattr(inner, "model_fields") and isinstance(val, list):
            out[key] = [_keep_fields(inner, x) if isinstance(x, dict) else x for x in val]
        elif hasattr(ann, "model_fields") and isinstance(val, dict):
            out[key] = _keep_fields(ann, val)
        else:
            # Optional[Model]
            for a in args:
                if hasattr(a, "model_fields") and isinstance(val, dict):
                    val = _keep_fields(a, val)
                    break
            out[key] = val
    return out


def _extract_remedy(html: str) -> str:
    m = re.search(
        r'(<div class="ev-label">What you can actually do about it</div>.*?)(?=<footer>)',
        html,
        re.S,
    )
    return m.group(1).strip() if m else ""


def regen_life() -> None:
    meta = json.loads(
        (REVIEW / "llm_on_new" / "meera_1990-01-15_delhi_llm_meta.json").read_text(
            encoding="utf-8"
        )
    )
    raw = dict(meta["_facts"])
    raw["vedic_context"] = {
        "period_lord": "Rahu",
        "sub_period_lord": "Jupiter",
        "mahadasha": "Rahu",
        "antardasha": "Jupiter",
        "lagna": "Aries",
        "nakshatra": "Purva Phalguni",
        "start": "",
        "end": str(raw.get("phase_end") or "2026-10-11"),
        "rising_sign": "Aries",
        "moon_sign": "Leo",
    }
    paid_src = _keep_fields(ReportFacts, raw)
    paid_facts = ReportFacts.model_validate(paid_src)
    paid_facts.life_state = build_life_state(
        list(paid_facts.cards),
        phase_tone=paid_facts.phase_tone,
        needs_care=list(paid_facts.hardest_areas or []),
    )
    paid_facts.vedic_context = VedicContext.model_validate(raw["vedic_context"])
    for card in paid_facts.cards:
        planets = list(card.allowed_planets or [])
        for lord in ("Rahu", "Jupiter"):
            if lord not in planets:
                planets.append(lord)
        card.allowed_planets = planets[:8]

    pc = {"lagna": {"sign": "Aries"}, "planets": {"Moon": {"sign": "Leo"}}}
    old_paid = (REVIEW / "life_state" / "meera_paid.html").read_text(encoding="utf-8")
    remedy = _extract_remedy(old_paid)

    out_dir = REVIEW / "life_state"
    out_dir.mkdir(parents=True, exist_ok=True)
    for access, name in (("paid", "meera_paid.html"), ("free", "meera_free.html")):
        facts = paid_facts.model_copy(deep=True)
        facts.access = access
        prose = conversational_fallback(facts)
        html = RC.render(
            pc,
            name="Meera",
            price=298,
            today=TODAY,
            paid=(access == "paid"),
            cards=list(facts.cards),
            prose=prose,
            remedy_html=remedy if access == "paid" else "",
        )
        (out_dir / name).write_text(html, encoding="utf-8")
        print(f"life {access}: basis={prose.get('astrological_basis','')[:160]!r}")
        print(f"  phase={prose['current_phase'][:140]!r}")


def regen_palm() -> None:
    raw = json.loads((REVIEW / "palm_state" / "facts.json").read_text(encoding="utf-8"))
    paid_src = _keep_fields(PalmFacts, raw)
    paid_facts = PalmFacts.model_validate(paid_src)
    aspects = [
        {
            "key": a.aspect,
            "title": a.title,
            "strength": a.strength,
        }
        for a in paid_facts.aspects
    ]
    raw_hand = {
        "confluence": {
            "dominant_hand": paid_facts.dominant_hand or "right",
            "life_aspects": aspects,
        }
    }
    out_dir = REVIEW / "palm_state"
    out_dir.mkdir(parents=True, exist_ok=True)
    for access, name in (("paid", "meera_palm_paid.html"), ("free", "meera_palm_free.html")):
        facts = paid_facts.model_copy(deep=True)
        facts.access = access
        prose = conversational_palm_fallback(facts)
        html = PC.render(
            raw_hand,
            name="Meera",
            age=int(facts.age_years or 30),
            dominant=facts.dominant_hand or "right",
            paid=(access == "paid"),
            price=499,
            prose=prose,
        )
        (out_dir / name).write_text(html, encoding="utf-8")
        print(f"palm {access}: stage={prose['current_phase'][:160]!r}")
        char = (prose.get("areas") or {}).get("character") or {}
        health = (prose.get("areas") or {}).get("health") or {}
        print(f"  character outlook={char.get('outlook', '')[:120]!r}")
        print(f"  health outlook={health.get('outlook', '')[:120]!r}")


if __name__ == "__main__":
    regen_life()
    regen_palm()
    print("done")
