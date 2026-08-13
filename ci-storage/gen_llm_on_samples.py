"""Generate LLM-on peer HTML, one report at a time (20 RPM endpoint).

Runs inside the API container:
  docker exec -e LLM_ENABLED=1 -e LLM_CONCURRENCY=1 -e LLM_MIN_INTERVAL=3.5 \\
    -e LLM_GEN_ONLY=meera ... python /tmp/gen_llm_on_samples.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import date
from pathlib import Path

os.environ.setdefault("LLM_ENABLED", "1")
os.environ["LLM_CONCURRENCY"] = os.environ.get("LLM_CONCURRENCY") or "1"

sys.path[:0] = ["/app/engines/astro", "/app", "/app/engines"]

OUT = Path("/tmp/review_samples/llm_on")
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
    stats = llm.get("stats") or {}
    paid_meta = llm.get("paid") or {}
    row = {
        "name": name,
        "free_bytes": len(free),
        "paid_bytes": len(paid),
        "llm_enabled": bool(llm.get("enabled")),
        "unlock_free": free.count('data-unlock="1"'),
        "accepted": int(stats.get("accepted") or (paid_meta.get("stats") or {}).get("accepted") or 0),
        "rejected": int(stats.get("rejected") or (paid_meta.get("stats") or {}).get("rejected") or 0),
        "fallback_used": bool(paid_meta.get("fallback_used") or llm.get("fallback_used")),
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
    return _write("horary_llm", free, paid, meta)


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

    truth = None
    facts = (meta or {}).get("_facts") or {}
    if isinstance(facts, dict):
        truth = facts.get("truth_source")
    return _write("user_question_llm", free, paid, meta, truth_source=truth)


def gen_daily() -> dict:
    print("[daily] ...", flush=True)
    from astro_precompute import resolve_precompute
    from daily_moon_prediction import compute_daily_moon_guide
    import report_render as RD

    s = MEERA
    pc = resolve_precompute(
        s["name"], s["dob"], birth_time=s["tob"],
        latitude=s["lat"], longitude=s["lon"],
        timezone=s["tz"], place_name=s["place"], gender=s["gender"])
    target = date(2026, 8, 12)
    data = compute_daily_moon_guide(
        pc, target,
        latitude=s["lat"], longitude=s["lon"], timezone=s["tz"])
    free, paid, meta = RD.daily(
        data if isinstance(data, dict) else {},
        lat=s["lat"], lon=s["lon"], tz=s["tz"], day=target,
        name=s["name"], price=298, pc=pc)
    return _write(
        "daily_llm", free, paid, meta,
        has_personal_focus=("Your most personal Moon transit today" in paid
                            or "personal" in paid.lower()),
        note="daily is not in LLM_TABS; template prose expected",
    )


def main() -> int:
    only = (os.environ.get("LLM_GEN_ONLY") or "").strip().lower()
    print("LLM_ENABLED=", os.environ.get("LLM_ENABLED", "<unset>"),
          "CONCURRENCY=", os.environ.get("LLM_CONCURRENCY"),
          "MIN_INTERVAL=", os.environ.get("LLM_MIN_INTERVAL"),
          "ONLY=", only or "<all>",
          flush=True)

    summary_path = OUT / "summary.json"
    summary: dict = {"astro": [], "horary": None, "user_question": None, "daily": None}
    if summary_path.is_file():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary.setdefault("astro", [])
        except Exception:
            pass

    def persist() -> None:
        summary_path.write_text(
            json.dumps(summary, indent=2, default=str), encoding="utf-8")

    def replace_astro(row: dict) -> None:
        summary["astro"] = [
            r for r in (summary.get("astro") or []) if r.get("name") != row["name"]]
        summary["astro"].append(row)

    jobs = []
    if only in ("", "meera", "astro"):
        jobs.append(("meera", lambda: gen_astro(MEERA, "meera_1990-01-15_delhi_llm")))
    if only in ("", "ramesh", "astro"):
        jobs.append(("ramesh", lambda: gen_astro(OVERSAMPLE[0], "ramesh_1986-03-08_delhi_llm")))
    if only in ("", "suresh", "astro"):
        jobs.append(("suresh", lambda: gen_astro(OVERSAMPLE[1], "suresh_1990-01-12_delhi_llm")))
    if only in ("", "gyanesh", "astro"):
        jobs.append(("gyanesh", lambda: gen_astro(OVERSAMPLE[2], "gyanesh_2012-01-01_hyderabad_llm")))
    if only in ("", "horary"):
        jobs.append(("horary", gen_horary))
    if only in ("", "question", "user_question"):
        jobs.append(("user_question", gen_user_question))
    if only in ("", "daily"):
        jobs.append(("daily", gen_daily))

    if not jobs:
        print(f"unknown LLM_GEN_ONLY={only}", file=sys.stderr)
        return 2

    fails = []
    for i, (key, fn) in enumerate(jobs):
        if i:
            pause = float(os.environ.get("LLM_REPORT_GAP", "8") or 8)
            print(f"[gap] sleeping {pause:.0f}s before {key}", flush=True)
            time.sleep(pause)
        try:
            row = fn()
        except Exception as exc:  # noqa: BLE001
            print(f"[{key}] FAILED: {exc}", flush=True)
            row = {"ok": False, "error": str(exc), "name": key}
            fails.append(f"{key}:error")
        if key in ("horary", "user_question", "daily"):
            summary[key] = row
        else:
            replace_astro(row)
            if key == "meera" and row.get("ok") is not False:
                for tier in ("free", "paid"):
                    src = OUT / f"meera_1990-01-15_delhi_llm_{tier}.html"
                    if src.is_file():
                        (OUT / f"astro_full_report_llm_{tier}.html").write_bytes(src.read_bytes())
        persist()
        print(json.dumps(row, indent=2, default=str), flush=True)
        if row.get("ok") is False:
            continue
        if key != "daily" and not row.get("llm_enabled"):
            fails.append(f"{key}:llm_off")
        if key != "daily" and row.get("unlock_free", 0) < 1:
            fails.append(f"{key}:unlock={row.get('unlock_free')}")

    persist()
    print(json.dumps(summary, indent=2, default=str), flush=True)
    if fails:
        print("FAILED:", ", ".join(fails), file=sys.stderr)
        return 1
    print("OK — wrote", OUT, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
