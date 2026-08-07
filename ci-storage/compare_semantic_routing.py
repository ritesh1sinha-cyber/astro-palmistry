#!/usr/bin/env python3
"""Compare keyword-only vs MiniLM semantic routing for Phase 1 questions.

Run from repo root:
  set PYTHONPATH=engines;engines/astro
  python ci-storage/compare_semantic_routing.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "engines"), str(ROOT / "engines" / "astro"), str(ROOT)]


QUESTIONS = [
    "Will I get the promotion this year?",
    "How have the last six months been for money and work?",
    "Will my career move forward soon?",
    "Profession feels stuck — when does it open?",  # paraphrased, no 'job' keyword
    "Will I relocate abroad for work?",
    "Is marriage likely in the next two years?",
]


def keyword_only_house(q: str) -> dict:
    """Simulate pre-MiniLM keyword path for western + client houses."""
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
    return {
        "primary_house": house_hits[0][0] if house_hits else None,
        "topic": topic,
        "method": "keyword_only",
    }


def main() -> None:
    from local_models import model_status, resolve_minilm
    import semantic_fallback
    semantic_fallback.install()

    st = model_status()
    print("=== model_status ===")
    print(json.dumps(st, indent=2))
    try:
        print("active path:", resolve_minilm())
    except FileNotFoundError as e:
        print("NO MODEL:", e)
        sys.exit(1)

    print("degraded_lexical:", semantic_fallback.degraded())
    print()

    import semantic_question as SQ
    from western_horary_rules import parse_question
    from client_question_engine import route_client_question
    from question_answer import classify

    rows = []
    for q in QUESTIONS:
        kw = keyword_only_house(q)
        sem = SQ.route(q)
        wh = parse_question(q)
        cq = route_client_question(q)
        qa = classify(q)
        row = {
            "question": q,
            "keyword_house": kw["primary_house"],
            "keyword_topic": kw["topic"],
            "minilm_house": sem.primary_house,
            "minilm_domain": sem.domain,
            "minilm_topic": sem.topic,
            "minilm_method": sem.method,
            "house_score": round(sem.house_score, 3),
            "western_house": wh["house"],
            "client_house": cq.primary_house,
            "client_domain": cq.domain,
            "qa_topic": qa.key,
            "improved": (
                kw["primary_house"] is None and sem.primary_house is not None
            ) or (
                kw["primary_house"] != sem.primary_house and sem.method == "minilm"
            ),
        }
        rows.append(row)
        print("---")
        print(q)
        print(f"  keyword -> house={kw['primary_house']} topic={kw['topic']}")
        print(f"  MiniLM  -> house={sem.primary_house} domain={sem.domain} "
              f"topic={sem.topic} method={sem.method} score={sem.house_score:.2f}")
        print(f"  western -> house={wh['house']}  client -> H{cq.primary_house}/{cq.domain}  "
              f"QA topic={qa.key}")

    out = ROOT / "ci-storage" / "semantic_routing_compare.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"model": st, "rows": rows}, indent=2), encoding="utf-8")
    improved = sum(1 for r in rows if r["improved"])
    print()
    print(f"Wrote {out}")
    print(f"Paraphrase / keyword-miss cases improved: {improved}/{len(rows)}")
    if st.get("active") != "paraphrase-multilingual-MiniLM-L12-v2":
        print("WARNING: expected paraphrase-multilingual-MiniLM-L12-v2 as active model")
        sys.exit(2)
    if semantic_fallback.degraded():
        print("WARNING: still on lexical fallback — install torch/ST weights")
        sys.exit(3)
    print("OK — MiniLM multilingual active")


if __name__ == "__main__":
    main()
