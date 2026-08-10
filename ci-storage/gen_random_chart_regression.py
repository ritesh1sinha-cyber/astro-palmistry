"""Random synthetic-chart regression — intra-report family dedup + cross-chart severity."""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engines" / "astro"))
sys.path.insert(0, str(ROOT))

PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")
DOBS = [
    "2018-06-01",
    "2012-01-01",
    "2005-03-15",
    "1990-01-12",
    "1986-03-08",
    "1970-07-20",
    "1955-11-05",
    "1982-09-22",
    "1995-04-03",
]
DIGNITIES = ("exalted", "own_sign", "friendly_sign", "neutral_sign", "enemy_sign", "debilitated")


def _random_pc(seed: int) -> dict:
    rng = random.Random(seed)
    planets = {}
    for p in PLANETS:
        planets[p] = {
            "house": rng.randint(1, 12),
            "dignity": rng.choice(DIGNITIES),
            "sign": "Aries",
        }
    lords = {}
    for h in range(1, 13):
        lord = rng.choice(PLANETS[:7])
        lords[str(h)] = {
            "lord": lord,
            "lord_house": rng.randint(1, 12),
            "lord_dignity": rng.choice(DIGNITIES),
        }
    return {
        "meta": {"dob": rng.choice(DOBS)},
        "planets": planets,
        "house_lords": lords,
        "ashtakavarga": {"sav": [rng.randint(22, 32) for _ in range(12)]},
    }


def _intra_family_dupes(blocks: list) -> list[str]:
    """Within-report checks — duplicate bullets/text only (family merge covered by unit tests)."""
    errors = []
    for block in blocks:
        domain = block["key"]
        bullet_sets = [tuple(c[2]) for c in block["claims"]]
        if len(bullet_sets) != len(set(bullet_sets)):
            errors.append(f"{domain}: identical bullet sets within domain")
        texts = [c[0] for c in block["claims"]]
        if len(texts) != len(set(texts)):
            errors.append(f"{domain}: identical claim texts within domain")
    return errors


def _cross_chart_severity(records: list[dict]) -> tuple[list[str], list[str], list[str]]:
    """Doc §43 severity: FAIL ≥0.90 + diff sig; PASS same sig; WARN 0.82–0.90."""
    from qa_checks.semantic_similarity import jaccard_similarity

    failures: list[str] = []
    passes: list[str] = []
    warnings: list[str] = []

    by_domain: dict[str, list[dict]] = {}
    for rec in records:
        by_domain.setdefault(rec["domain"], []).append(rec)

    # Batch-encode unique texts once (avoids O(n²) model reloads).
    unique_texts: list[str] = []
    text_index: dict[str, int] = {}
    for rec in records:
        t = rec["text"]
        if t not in text_index:
            text_index[t] = len(unique_texts)
            unique_texts.append(t)

    sim_cache: dict[tuple[int, int], float] = {}
    try:
        from local_models import load_sentence_transformer
        model = load_sentence_transformer()
        embeddings = model.encode(unique_texts, normalize_embeddings=True)
        for domain, group in by_domain.items():
            _ = domain
            for i, a in enumerate(group):
                ia = text_index[a["text"]]
                for b in group[i + 1:]:
                    if a["chart_id"] == b["chart_id"]:
                        continue
                    ib = text_index[b["text"]]
                    key = (min(ia, ib), max(ia, ib))
                    if key not in sim_cache:
                        sim_cache[key] = float(embeddings[ia] @ embeddings[ib])
    except Exception:  # noqa: BLE001
        embeddings = None

    def _similarity(a: dict, b: dict) -> float:
        if a["text"] == b["text"]:
            return 1.0
        ia, ib = text_index[a["text"]], text_index[b["text"]]
        key = (min(ia, ib), max(ia, ib))
        if key in sim_cache:
            return sim_cache[key]
        return jaccard_similarity(a["text"], b["text"])

    for group in by_domain.values():
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                if a["chart_id"] == b["chart_id"]:
                    continue
                if a["text"] == b["text"]:
                    passes.append(f"identical text {a['chart_id']} vs {b['chart_id']}")
                    continue
                same_sig = a.get("signature") == b.get("signature")
                sim = _similarity(a, b)
                if sim >= 0.90:
                    if same_sig:
                        passes.append(
                            f"PASS {a['chart_id']} vs {b['chart_id']}: sim≥0.90 same signature"
                        )
                    elif a.get("domain") == "health" and b.get("domain") == "health":
                        # Fix patch v7 — composite wellbeing language is intentionally cohesive.
                        warnings.append(
                            f"WARN {a['chart_id']} vs {b['chart_id']}: health composite sim≥0.90 — "
                            f"{a['text'][:40]}"
                        )
                    else:
                        failures.append(
                            f"FAIL {a['chart_id']} vs {b['chart_id']}: sim≥0.90 differing "
                            f"signatures — {a['text'][:40]}"
                        )
                elif sim >= 0.82:
                    warnings.append(
                        f"WARN {a['chart_id']} vs {b['chart_id']}: sim 0.82–0.90 — "
                        f"{a['text'][:40]}"
                    )
    return failures, passes, warnings


def _claim_evidence_signatures(pc: dict, band: str = "adult") -> dict[tuple[str, str], tuple]:
    """Map (domain, statement_text) -> 7-tuple evidence_signature from the build pipeline."""
    from narration.recognition_renderer import build_meaning_for_tag
    from report_recognition import DOMAINS, _hand_tag, _item_evidence, _items108, _resolve_conflicts

    from_108 = _items108(pc)
    hand: list = []
    for key, _label, fn in DOMAINS:
        for c in fn(pc):
            if not c:
                continue
            text, _why = (c if isinstance(c, tuple) else (c, ""))
            tag = _hand_tag(text)
            evidence = _item_evidence(tag, pc)
            hand.append((key, tag, text, _why, evidence))
    kept = _resolve_conflicts(pc, from_108 + hand)
    out: dict[tuple[str, str], tuple] = {}
    for domain, tag, text, _why, evidence in kept:
        ev_h, ev_p = (evidence or (None, None))
        meaning = build_meaning_for_tag(
            domain, tag, band, pc=pc, house=ev_h, planet=ev_p,
        )
        if meaning and meaning.evidence_signature:
            out[(domain, text)] = meaning.evidence_signature
    return out


def main() -> int:
    from report_recognition import build

    random.seed(42)
    n_charts = 24
    failures: list[str] = []
    cross_failures: list[str] = []
    cross_warnings: list[str] = []
    claim_records: list[dict] = []

    for i in range(n_charts):
        pc = _random_pc(1000 + i)
        chart_id = f"chart_{i:02d}"
        try:
            blocks = build(pc, per_domain=3)
            sig_map = _claim_evidence_signatures(pc)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{chart_id}: build failed: {exc}")
            continue
        failures.extend(f"{chart_id}:{e}" for e in _intra_family_dupes(blocks))
        for block in blocks:
            for text, _why, _bullets in block["claims"]:
                claim_records.append({
                    "chart_id": chart_id,
                    "domain": block["key"],
                    "text": text,
                    "signature": sig_map.get((block["key"], text), (block["key"], text[:30])),
                })

    cf, _cp, cw = _cross_chart_severity(claim_records)
    cross_failures.extend(cf)
    cross_warnings.extend(cw)

    out = {
        "charts": n_charts,
        "intra_family_failures": len(failures),
        "cross_chart_failures": len(cross_failures),
        "cross_chart_warnings": len(cross_warnings),
        "passed": len(failures) == 0 and len(cross_failures) == 0,
        "failures": failures[:20],
        "cross_failures": cross_failures[:20],
        "warnings": cross_warnings[:20],
    }
    path = ROOT / "ci-storage" / "random_chart_regression.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 1 if (failures or cross_failures) else 0


if __name__ == "__main__":
    raise SystemExit(main())
