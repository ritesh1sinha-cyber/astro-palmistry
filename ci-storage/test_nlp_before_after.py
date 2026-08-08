#!/usr/bin/env python3
"""NLP before/after quality check — keyword-era vs MiniLM + amount-aware answers.

Captures the regression the product saw: "How much hike…" answered as bare "Yes"
because the question was treated as yes/no instead of magnitude.

Run from repo root (needs ~2–3 GB free RAM for real MiniLM):
  set PYTHONPATH=engines;engines/astro
  python ci-storage/test_nlp_before_after.py

Writes: ci-storage/nlp_before_after.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "engines"), str(ROOT / "engines" / "astro"), str(ROOT)]

# Natural-language customer questions (not keyword templates)
CASES = [
    {
        "id": "hike_amount",
        "question": "How much hike can I expect this year?",
        "expect_form": "amount",
        "expect_houses": {10, 11, 2},
        "forbid_answers": {"yes", "no"},
        "forbid_western_prefix": ("yes", "no", "likely yes", "unlikely"),
        "note": "Classic failure: answered Yes without understanding magnitude",
    },
    {
        "id": "hike_percent",
        "question": "What percentage salary increase is likely for me?",
        "expect_form": "amount",
        "expect_houses": {10, 11, 2},
        "forbid_answers": {"yes", "no"},
        "forbid_western_prefix": ("yes", "no", "likely yes", "unlikely"),
        "note": "Amount phrasing without the word hike",
    },
    {
        "id": "hike_yesno",
        "question": "Will I get a hike this year?",
        "expect_form": "yes_no",
        "expect_houses": {10, 11, 2},
        "forbid_answers": set(),
        "forbid_western_prefix": (),
        "note": "True yes/no — binary answer is correct here",
    },
    {
        "id": "career_paraphrase",
        "question": "Profession feels stuck — when does it open?",
        "expect_form": "when",
        "expect_houses": {10, 11, 6},
        "forbid_answers": set(),
        "forbid_western_prefix": (),
        "note": "Paraphrase with weak keywords — MiniLM should keep career/H10",
    },
    {
        "id": "money_past",
        "question": "How have the last six months been for money and work?",
        "expect_form": "general",  # or amount-ish; not yes_no
        "expect_houses": {2, 10, 11, 6},
        "forbid_answers": set(),
        "forbid_western_prefix": (),
        "note": "Past window — finance/career houses, not marriage/travel drift",
    },
    {
        "id": "marriage_yesno",
        "question": "Is marriage likely in the next two years?",
        "expect_form": "yes_no",
        "expect_houses": {7},
        "forbid_answers": set(),
        "forbid_western_prefix": (),
        "note": "Control: clear yes/no marriage question",
    },
]


def _old_intent(q: str) -> str:
    """Pre-fix intent detector (no amount awareness; bare 'year' → when)."""
    ql = q.lower()
    if re.search(r"\b(recover|recovery|cure|heal|get well|remission)\b", ql):
        return "recovery"
    if re.search(r"\b(court|litigation|lawsuit|case|win the case|legal battle|bail)\b", ql):
        return "legal_outcome"
    if re.search(r"\b(when|timing|date|month|year|how long)\b", ql):
        return "when"
    if re.search(r"\b(how serious|severity|danger|life threat)\b", ql):
        return "severity"
    if re.search(r"\b(will|can|shall|should|is it possible|going to)\b", ql):
        return "yes_no"
    # Old path: "how much…" / "what %" often fell to general → synthesizer said yes
    return "general"


def _keyword_route(q: str) -> dict[str, Any]:
    from client_question_engine import HOUSE_KEYWORDS
    from horary_precompute import TOPIC_KEYWORDS

    ql = q.lower()
    house_hits = []
    for h, kws in HOUSE_KEYWORDS.items():
        n = sum(1 for kw in kws if kw in ql)
        if n:
            house_hits.append((h, n))
    house_hits.sort(key=lambda x: (-x[1], x[0]))
    topic = "general"
    for t in ["disease_cure", "disease", "children", "marriage", "career",
              "health", "finance", "travel", "education"]:
        if any(kw in ql for kw in TOPIC_KEYWORDS.get(t, [])):
            topic = t
            break
    intent = _old_intent(q)
    # Old synthesizer: general + any positive lean → "yes"
    if intent in ("yes_no", "general"):
        fake_answer = "yes"  # the bug: amount questions collapsed here
    elif intent == "when":
        fake_answer = "window_found"
    else:
        fake_answer = intent
    return {
        "method": "keyword_only",
        "intent": intent,
        "primary_house": house_hits[0][0] if house_hits else None,
        "topic": topic,
        "answer": fake_answer,
        "headline": (
            "Yes — career is supported in your chart"
            if fake_answer == "yes"
            else fake_answer
        ),
        "western_amount": False,
        "western_verdict_shape": "Yes/No (binary)",
    }


def _after_route(q: str) -> dict[str, Any]:
    import semantic_question as SQ
    from client_question_engine import (
        _detect_intent,
        route_client_question,
        synthesize_answer,
        TechniqueVerdict,
    )
    from western_horary_rules import parse_question

    sem = SQ.route(q)
    ctx = route_client_question(q)
    intent = _detect_intent(q)
    wh = parse_question(q)

    # Lightweight synthesizer with neutral technique votes so answer *shape*
    # is driven by intent, not a specific birth chart.
    dummy = [
        TechniqueVerdict("vimshottari", "period", "Vedic", "positive", note="test"),
        TechniqueVerdict("varga", "divisional", "Vedic", "positive", note="test"),
        TechniqueVerdict("kp", "sublord", "KP", "neutral", note="test"),
    ]
    syn = synthesize_answer(ctx, dummy)

    return {
        "method": sem.method,
        "intent": intent,
        "domain": sem.domain,
        "primary_house": ctx.primary_house,
        "houses": list(ctx.houses),
        "topic": ctx.topic,
        "house_score": round(float(sem.house_score or 0), 3),
        "answer": syn["answer"],
        "headline": syn["headline"],
        "western_house": wh["house"],
        "western_amount": bool(wh.get("amount")),
        "western_when": bool(wh.get("when")),
        "semantic_house": wh.get("semantic_house"),
    }


def _grade(case: dict, before: dict, after: dict) -> dict[str, Any]:
    qid = case["id"]
    fails: list[str] = []
    improves: list[str] = []

    # After: intent form
    if case["expect_form"] == "amount":
        if after["intent"] != "amount":
            fails.append(f"after intent={after['intent']!r} want amount")
        else:
            improves.append("intent=amount")
        if after["answer"] in case["forbid_answers"]:
            fails.append(f"after answer still binary {after['answer']!r}")
        else:
            improves.append(f"answer={after['answer']}")
        if not after.get("western_amount"):
            fails.append("western parse_question.amount is False")
        else:
            improves.append("western amount_mode")
        if before["answer"] in ("yes", "no") and after["answer"] not in ("yes", "no"):
            improves.append("fixed yes-collapse on amount question")

    if case["expect_form"] == "yes_no":
        if after["intent"] != "yes_no":
            # "Is marriage likely" may be general — allow yes_no or general
            if "will" in case["question"].lower() or "is " in case["question"].lower()[:3]:
                if after["intent"] not in ("yes_no", "general"):
                    fails.append(f"yes/no question got intent={after['intent']}")
        if after["answer"] in ("increase_favoured", "increase_limited", "amount_unclear"):
            fails.append("true yes/no wrongly treated as amount")

    if case["expect_form"] == "when":
        if after["intent"] != "when":
            fails.append(f"when-question intent={after['intent']}")

    # House / domain
    expect_h = case["expect_houses"]
    after_h = set(after.get("houses") or []) | {after.get("primary_house")}
    after_h.discard(None)
    if after_h.isdisjoint(expect_h):
        fails.append(f"houses {sorted(after_h)} miss expected {sorted(expect_h)}")
    else:
        improves.append(f"house ok primary={after.get('primary_house')}")

    # Before→after: paraphrase cases where keyword house was None
    if before.get("primary_house") is None and after.get("primary_house"):
        improves.append("MiniLM filled keyword miss")

    if before["intent"] != "amount" and after["intent"] == "amount" and case["expect_form"] == "amount":
        improves.append("amount intent newly detected")

    quality = "improved" if improves and not fails else ("regressed" if fails else "same")
    if fails and improves:
        quality = "mixed"

    return {
        "id": qid,
        "quality": quality,
        "fails": fails,
        "improves": improves,
        "before_bad_yes_on_amount": (
            case["expect_form"] == "amount" and before["answer"] in ("yes", "no")
        ),
    }


def main() -> int:
    from local_models import model_status, resolve_minilm
    import semantic_fallback

    semantic_fallback.install()
    st = model_status()
    try:
        path = resolve_minilm()
    except FileNotFoundError as exc:
        print("NO MODEL:", exc)
        return 1

    print("=== NLP before / after ===")
    print("model:", st.get("active"), path)
    print()

    rows = []
    n_imp = n_reg = n_same = n_mix = 0
    for case in CASES:
        q = case["question"]
        before = _keyword_route(q)
        after = _after_route(q)
        grade = _grade(case, before, after)
        row = {
            "question": q,
            "note": case["note"],
            "before": before,
            "after": after,
            "grade": grade,
        }
        rows.append(row)
        qlt = grade["quality"]
        if qlt == "improved":
            n_imp += 1
        elif qlt == "regressed":
            n_reg += 1
        elif qlt == "mixed":
            n_mix += 1
        else:
            n_same += 1

        print(f"--- {case['id']}: {q}")
        print(f"  BEFORE  intent={before['intent']:10} house={before['primary_house']}  "
              f"answer={before['answer']!r}")
        print(f"          headline={before['headline'][:80]}")
        print(f"  AFTER   intent={after['intent']:10} house={after['primary_house']}  "
              f"domain={after.get('domain')} method={after['method']}")
        print(f"          answer={after['answer']!r}")
        print(f"          headline={after['headline'][:90]}")
        print(f"          western amount={after.get('western_amount')} "
              f"house={after.get('western_house')}")
        print(f"  GRADE   {grade['quality'].upper()}  "
              f"+{grade['improves']}  !{grade['fails']}")
        print()

    out = {
        "model": st,
        "summary": {
            "improved": n_imp,
            "regressed": n_reg,
            "mixed": n_mix,
            "same": n_same,
            "total": len(CASES),
        },
        "cases": rows,
    }
    out_path = ROOT / "ci-storage" / "nlp_before_after.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    print(f"Summary: improved={n_imp} mixed={n_mix} same={n_same} regressed={n_reg}")

    # Hard fail if the hike-amount case still answers yes/no
    hike = next(r for r in rows if r["grade"]["id"] == "hike_amount")
    if hike["after"]["answer"] in ("yes", "no") or hike["after"]["intent"] != "amount":
        print("FAIL — hike amount still misunderstood")
        return 2
    if n_reg:
        print("FAIL — regressions present")
        return 3
    print("OK — amount questions no longer collapse to Yes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
