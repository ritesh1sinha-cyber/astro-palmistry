"""Generate LLM-off peer HTML: 4 astro samples + horary + user question.

Runs inside the API container:
  docker exec -e LLM_ENABLED=0 ... python /tmp/gen_llm_off_samples.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

sys.path[:0] = ["/app/engines/astro", "/app", "/app/engines"]

OUT = Path("/tmp/review_samples/llm_off")
OUT.mkdir(parents=True, exist_ok=True)

MEERA = {
    "name": "Meera Nair", "dob": "1990-01-15", "tob": "12:00",
    "lat": 28.6139, "lon": 77.2090, "tz": 5.5,
    "place": "New Delhi", "gender": 0,
}
OVERSAMPLE = [
    {"slug": "ramesh_1986-03-08_delhi", "name": "Ramesh",
     "dob": "1986-03-08", "tob": "13:00", "lat": 28.6139, "lon": 77.209,
     "tz": 5.5, "place": "New Delhi", "gender": 0},
    {"slug": "suresh_1990-01-12_delhi", "name": "Suresh",
     "dob": "1990-01-12", "tob": "00:05", "lat": 28.6139, "lon": 77.209,
     "tz": 5.5, "place": "New Delhi", "gender": 0},
    {"slug": "gyanesh_2012-01-01_hyderabad", "name": "Gyanesh",
     "dob": "2012-01-01", "tob": "10:00", "lat": 17.385, "lon": 78.4867,
     "tz": 5.5, "place": "Hyderabad", "gender": 0},
]


def _write(name: str, free: str, paid: str, meta: dict, **extra) -> dict:
    (OUT / f"{name}_free.html").write_text(free, encoding="utf-8")
    (OUT / f"{name}_paid.html").write_text(paid, encoding="utf-8")
    (OUT / f"{name}_meta.json").write_text(
        json.dumps(meta, indent=2, default=str), encoding="utf-8")
    llm = (meta or {}).get("llm") or {}
    row = {
        "name": name,
        "free_bytes": len(free),
        "paid_bytes": len(paid),
        "llm_enabled": bool(llm.get("enabled")),
        "unlock_free": free.count('data-unlock="1"'),
    }
    row.update(extra)
    return row


def gen_astro(sample: dict, slug: str) -> dict:
    from astro_precompute import resolve_precompute
    import deep_evidence as DE
    import report_render as RD

    print(f"[astro] {slug} ...", flush=True)
    pc = resolve_precompute(
        sample["name"], sample["dob"], birth_time=sample["tob"],
        latitude=sample["lat"], longitude=sample["lon"],
        timezone=sample["tz"], place_name=sample["place"],
        gender=sample.get("gender", 0))
    DE.begin(pc, lat=sample["lat"], lon=sample["lon"], tz=sample["tz"])
    try:
        free, paid, meta = RD._full_report_inner(
            pc, name=sample["name"], question="", today=date.today(),
            price=298, bundle_price=298,
            lat=sample["lat"], lon=sample["lon"], tz=sample["tz"],
            first=sample["name"].split()[0])
    finally:
        DE.end()
    return _write(slug, free, paid, meta)


def gen_horary() -> dict:
    """Mirror handlers.h_horary without auth/storage."""
    print("[horary] ...", flush=True)
    import report_render as RD

    question = "Will this job offer come through this year?"
    q_date, q_time = "2026-08-11", "18:00"
    location = "New Delhi, India"
    area = ""

    htmls, verdicts = {}, {}
    western_judgment: dict = {}
    vedic_customer: dict = {}

    try:
        import semantic_fallback
        semantic_fallback.install()
    except Exception:
        pass
    try:
        import semantic_question as SQ
        area = SQ.normalize_area("profession")
        SQ.route(question, area=area)
    except Exception as exc:  # noqa: BLE001
        print(f"[horary] semantic route skipped: {exc}", flush=True)

    vgen = None
    if os.getenv("ASTRO_HOTFIX", "1") == "1":
        try:
            import astro_hotfix
            vgen = astro_hotfix.horary_glyph_fix().generate_vedic_horary_html
        except Exception as exc:  # noqa: BLE001
            print(f"[horary] hotfix unavailable: {exc}", flush=True)
    if vgen is None:
        from vedic_horary_report import generate_vedic_horary_html as vgen
    try:
        try:
            h, j = vgen(question, q_date, q_time, location, "108", area=area)
        except TypeError:
            h, j = vgen(question, q_date, q_time, location, "108")
        htmls["vedic"] = h
        verdicts["vedic"] = {k: j.get(k) for k in ("verdict", "confidence", "score", "systems")}
        vedic_customer = j.get("customer") or {}
    except Exception as exc:  # noqa: BLE001
        verdicts["vedic"] = {"error": f"{type(exc).__name__}: {exc}"}

    try:
        from western_horary_report import generate_western_horary_html as wgen
        qh = None
        if area:
            try:
                import semantic_question as SQ
                qh = SQ.AREA_TO_HOUSE.get(area)
            except Exception:
                qh = None
        h, j = wgen(question, q_date, q_time, location, quesited_house=qh)
        htmls["western"] = h
        verdicts["western"] = {k: j.get(k) for k in ("verdict", "confidence")}
        western_judgment = j
    except Exception as exc:  # noqa: BLE001
        verdicts["western"] = {"error": f"{type(exc).__name__}: {exc}"}

    if not htmls:
        raise RuntimeError("both horary engines failed: " + json.dumps(verdicts))

    free, paid, meta = RD.horary(
        question=question, verdicts=verdicts,
        western_judgment=western_judgment,
        asked=f"{q_date} {q_time}",
        name="Meera",
        horary_price=298, full_report_price=1499,
        vedic_customer=vedic_customer)
    meta = {**(meta or {}), "verdicts": verdicts}
    return _write("horary_off", free, paid, meta)


def gen_user_question() -> dict:
    print("[user_question] ...", flush=True)
    from astro_precompute import resolve_precompute
    import deep_evidence as DE
    import report_render as RD

    s = MEERA
    question = "Will my career improve in the next two years?"
    area = "profession"
    route = None
    try:
        import semantic_fallback
        semantic_fallback.install()
    except Exception:
        pass
    try:
        import semantic_question as SQ
        area = SQ.normalize_area(area)
        route = SQ.route(question, area=area)
    except Exception as exc:  # noqa: BLE001
        print(f"[user_question] semantic route skipped: {exc}", flush=True)

    pc = resolve_precompute(
        s["name"], s["dob"], birth_time=s["tob"],
        latitude=s["lat"], longitude=s["lon"],
        timezone=s["tz"], place_name=s["place"], gender=s["gender"])
    DE.begin(pc, lat=s["lat"], lon=s["lon"], tz=s["tz"])
    try:
        free, paid, meta = RD.user_question(
            pc, question=question, route=route, area=area,
            name=s["name"], price=1499,
            lat=s["lat"], lon=s["lon"], tz=s["tz"])
    finally:
        DE.end()

    # Pull truth_source from facts if present
    truth = None
    facts = (meta or {}).get("_facts") or {}
    if isinstance(facts, dict):
        truth = facts.get("truth_source")
    return _write("user_question_off", free, paid, meta, truth_source=truth)


def main() -> int:
    print("LLM_ENABLED=", os.environ.get("LLM_ENABLED", "<unset>"), flush=True)
    summary: dict = {"astro": [], "horary": None, "user_question": None}

    meera = gen_astro(MEERA, "meera_1990-01-15_delhi")
    summary["astro"].append(meera)
    # Canonical peer names
    for tier in ("free", "paid"):
        src = OUT / f"meera_1990-01-15_delhi_{tier}.html"
        if src.is_file():
            (OUT / f"astro_full_report_{tier}.html").write_bytes(src.read_bytes())
            (OUT / f"astro_full_report_{tier}.html").write_bytes(src.read_bytes())

    for sample in OVERSAMPLE:
        summary["astro"].append(gen_astro(sample, sample["slug"]))

    try:
        summary["horary"] = gen_horary()
    except Exception as exc:  # noqa: BLE001
        print(f"[horary] FAILED: {exc}", flush=True)
        summary["horary"] = {"ok": False, "error": str(exc)}

    try:
        summary["user_question"] = gen_user_question()
    except Exception as exc:  # noqa: BLE001
        print(f"[user_question] FAILED: {exc}", flush=True)
        summary["user_question"] = {"ok": False, "error": str(exc)}

    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(json.dumps(summary, indent=2, default=str), flush=True)

    fails = []
    for row in summary["astro"]:
        if row.get("llm_enabled"):
            fails.append(f"astro:{row['name']}:llm_on")
        if row.get("unlock_free", 0) != 1:
            fails.append(f"astro:{row['name']}:unlock={row.get('unlock_free')}")
    for key in ("horary", "user_question"):
        row = summary.get(key) or {}
        if row.get("ok") is False:
            fails.append(f"{key}:error")
        elif row.get("llm_enabled"):
            fails.append(f"{key}:llm_on")
    if fails:
        print("FAILED:", ", ".join(fails), file=sys.stderr)
        return 1
    print("OK — wrote", OUT, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
