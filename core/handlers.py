"""
Job handlers — the only place that touches the two engines.

Everything here runs inside a worker process (never in an API request), writes
its output to object storage, and records a row in `reports`. Both engines are
imported lazily so an API replica never needs mediapipe or PyJHora installed.

The precompute cache is the scalability keystone: one ephemeris pass per unique
birth moment, reused by the report, the daily reading, muhurat and timing.
"""

from __future__ import annotations

import base64
import json
import os
import tempfile
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from .billing import (entitled, is_subscribed, month_period, use_quota,
                      pin_subscribed_daily_reports, daily_trial_grants_full,
                      daily_trial_remaining)
from .config import S
from .db import (get_or_create_chart, precompute_get, precompute_put,
                 report_insert)
from .store import report_keys, store

# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------
from core.errors import UserError, gender_code


def _as_date(v) -> date:
    if isinstance(v, date):
        return v
    y, m, d = (int(x) for x in str(v).split("-"))
    return date(y, m, d)


def precompute_for(chart: dict) -> dict:
    """Cached ephemeris pass. This is what makes 1 lakh users affordable."""
    cached = precompute_get(chart["chart_hash"])
    if cached:
        if chart.get("person_name"):
            cached.setdefault("meta", {})["client"] = chart["person_name"]
        return cached
    from astro_precompute import resolve_precompute
    pc = resolve_precompute(
        chart.get("person_name") or "Seeker", str(chart["dob"]),
        birth_time=str(chart["tob"]), latitude=float(chart["lat"]),
        longitude=float(chart["lon"]), timezone=float(chart["tz_offset"]),
        place_name=chart.get("place") or "", gender=gender_code(chart.get("gender")))
    precompute_put(chart["chart_hash"], pc)
    return pc


def _voice_ctx(pc: dict, chart: dict) -> dict:
    import astro_voice as V
    return V.context_from_pc(pc, name=chart.get("person_name") or "Seeker",
                             place=chart.get("place") or "",
                             tob=str(chart.get("tob") or ""))


def _save_report(user_id: str, chart_id: Optional[str], kind: str,
                 free_html: str, paid_html: str, meta: dict, paid: bool) -> dict:
    rid = str(uuid.uuid4())
    fk, pk = report_keys(rid)
    st = store()
    st.put(fk, (free_html or "").encode(), "text/html; charset=utf-8")
    st.put(pk, (paid_html or "").encode(), "text/html; charset=utf-8")

    # Persist fact-only JSON for the LLM chat layer (Phase 2). Never leave
    # the full facts blob in the customer-facing meta payload.
    meta = dict(meta or {})
    facts = meta.pop("_facts", None) or meta.pop("facts", None)
    if facts:
        try:
            from .store import facts_key as _facts_key
            fkey = _facts_key(rid)
            st.put(fkey, json.dumps(facts, default=str).encode("utf-8"),
                   "application/json; charset=utf-8")
            meta["facts_key"] = fkey
        except Exception as exc:  # noqa: BLE001
            print(f"[handlers] facts.json skipped: {exc}", flush=True)

    try:
        import sys
        from pathlib import Path
        eng = Path(__file__).resolve().parents[1] / "engines" / "astro"
        if str(eng) not in sys.path:
            sys.path.insert(0, str(eng))
        from llm.summary import attach_plain_summary
        lang = str(meta.get("language") or "en")
        meta = attach_plain_summary(
            meta, kind=kind, free_html=free_html or "",
            paid_html=paid_html or "", paid=bool(paid), facts=facts,
            lang=lang,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[handlers] plain summary skipped: {exc}", flush=True)

    # keep the id we generated so the storage keys match the row
    from sqlalchemy import text as _text

    from .db import jdump, now, tx
    with tx() as c:
        c.execute(_text(
            "INSERT INTO reports (id,user_id,chart_id,kind,paid,free_key,paid_key,"
            "meta,engine_version,created_at,expires_at)"
            " VALUES (:i,:u,:c,:k,:paid,:f,:p,:m,:v,:t,:e)"),
            {"i": rid, "u": user_id, "c": chart_id, "k": kind, "paid": bool(paid),
             "f": fk, "p": pk, "m": jdump(meta), "v": S.engine_version,
             "t": now(), "e": now() + timedelta(days=S.report_retention_days)})
    try:
        from .stats import increment_report_generation
        increment_report_generation(kind)
    except Exception:  # noqa: BLE001
        pass
    return {"reportId": rid, "paid": bool(paid), "meta": meta}


def _save_json_report(user_id: str, kind: str, *, free_payload: dict,
                      paid_payload: dict, meta: dict, paid: bool) -> dict:
    """
    Legacy JSON halves (older palm readings). New palm jobs use `_save_report`
    with HTML, same as astrology. Kept for any caller that still needs JSON.
    """
    rid = str(uuid.uuid4())
    shard = rid[:2]
    fk = f"reports/{shard}/{rid}/free.json"
    pk = f"reports/{shard}/{rid}/paid.json"
    st = store()
    st.put(fk, json.dumps(free_payload, default=str).encode(), "application/json")
    st.put(pk, json.dumps(paid_payload, default=str).encode(), "application/json")
    from sqlalchemy import text as _text

    from .db import jdump, now, tx
    with tx() as c:
        c.execute(_text(
            "INSERT INTO reports (id,user_id,chart_id,kind,paid,free_key,paid_key,"
            "meta,engine_version,created_at,expires_at)"
            " VALUES (:i,:u,NULL,:k,:paid,:f,:p,:m,:v,:t,:e)"),
            {"i": rid, "u": user_id, "k": kind, "paid": bool(paid), "f": fk, "p": pk,
             "m": jdump(meta), "v": S.engine_version, "t": now(),
             "e": now() + timedelta(days=S.report_retention_days)})
    try:
        from .stats import increment_report_generation
        increment_report_generation(kind)
    except Exception:  # noqa: BLE001
        pass
    return {"reportId": rid, "paid": bool(paid), "meta": meta}


# ===========================================================================
# palmistry
# ===========================================================================
def h_palm(user: dict, p: dict) -> dict:
    from palm_api.pipeline import analyze_image_paths

    tmp = Path(tempfile.mkdtemp(prefix="palm_"))
    run_id = uuid.uuid4().hex[:12]
    overlay_dir = tmp / "out"
    paths = []
    try:
        for hand in ("right", "left"):
            data = p.get(f"{hand}Hand") or ""
            if not data:
                continue
            if "," in data and data.strip().startswith("data:"):
                data = data.split(",", 1)[1]
            raw = base64.b64decode(data)
            if len(raw) < 2048:
                raise UserError("One of the palm photos is unreadable. Retake it in "
                                "bright light with the hand flat and open.")
            # filename carries the hand: palm_api._guess_hand reads it from there
            f = tmp / f"{run_id}_{hand}palm.jpg"
            f.write_bytes(raw)
            paths.append(f)
        if len(paths) < 2:
            raise UserError("Both palms are needed for a reading.")

        raw_result = analyze_image_paths(
            [str(x) for x in paths],
            active_hand=p.get("dominant", "right"), overlay_dir=overlay_dir)

        # overlays → object storage (proof + archive; HTML embeds them as data URIs)
        overlays = {}
        st = store()
        for hand in ("left", "right"):
            op = (raw_result.get(hand) or {}).get("overlay_path")
            if op and Path(op).is_file():
                key = f"overlays/{run_id}/{Path(op).name}"
                st.put(key, Path(op).read_bytes(), "image/jpeg")
                overlays[hand] = key

        # Same delivery shape as astrology: HTML halves in object storage,
        # signed /api/file links, iframe on the site. The old JSON card path
        # (build_palm_reading) is kept in palm_report.py but no longer served.
        from .palm_report import build_palm_html_reading
        price = S.price("palm_full") // 100
        lang = str(p.get("language") or "en")
        free_html, paid_html, meta = build_palm_html_reading(
            raw_result, p, price=price, lang=lang)
        meta = {**meta, "overlays": overlays, "price": price, "language": lang}
        paid = entitled(user["id"], "palm_full")
        saved = _save_report(user["id"], None, "palm",
                             free_html, paid_html, meta, paid)
        saved["price"] = meta["price"]
        saved["overlays"] = overlays
        return saved
    finally:
        for f in paths:
            f.unlink(missing_ok=True)
        if os.getenv("KEEP_UPLOADS", "0") != "1":
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


# ===========================================================================
# astrology
# ===========================================================================
def h_chart_summary(user: dict, p: dict) -> dict:
    import astro_voice as V
    chart = get_or_create_chart(user["id"], p)
    pc = precompute_for(chart)
    meta = pc.get("meta") or {}
    planets = pc.get("planets") or {}
    moon = planets.get("Moon") or {}
    vim = pc.get("vimshottari") or {}
    cur = vim.get("current") or {}
    if not cur:
        today = date.today().isoformat()
        for row in vim.get("sequence") or []:
            if str(row.get("start") or "") <= today <= str(row.get("end") or ""):
                cur = row
                break
    return {
        "chartId": chart["id"],
        "lagna": {"sign": meta.get("lagna_sign"), "degree": meta.get("lagna_degree"),
                  "nakshatra": meta.get("lagna_nakshatra"), "pada": meta.get("lagna_pada"),
                  "lord": meta.get("lagna_lord")},
        "moon": {"sign": moon.get("sign"), "nakshatra": moon.get("nakshatra")},
        "currentDasha": {"md": cur.get("md_lord") or cur.get("lord"),
                         "ad": cur.get("ad_lord"), "from": cur.get("start"),
                         "to": cur.get("end")},
        "age": meta.get("age"), "ayanamsa": meta.get("ayanamsa"),
        "personalNote": V.concise(V.humanise(V.chart_opening(_voice_ctx(pc, chart)))),
    }


def h_numerology(user: dict, p: dict) -> dict:
    """Every number and its verdict free, the working behind them locked.

    `report_render.numerology` now drives the real `numerology_report` engine
    rather than the thin reimplementation that used to live in `tab_renderers`:
    the Chaldean and Pythagorean ciphers, the 45-year dasha ring with its
    birthday years and nine slices, name harmony and name correction. Free gets
    the six numbers, the Lo Shu grid with its empty cells named, where the cycle
    stands today and whether the name agrees with the birth date. Paid gets the
    arithmetic, the dates and the fixes.
    """
    import report_render as RD
    name = p.get("name", "Seeker")
    free, paid_html, meta = RD.numerology(
        name, p["dob"], price=S.price("numerology_full") // 100)
    # The TAB is free — `numerology` is in billing.FREE_ITEMS, so gating on it
    # would make entitled() always true and nothing would ever lock. The years
    # ahead and the Lo Shu remedies are the paid half, sold as `numerology_full`
    # and included in the bundle.
    paid = entitled(user["id"], "numerology_full")
    saved = _save_report(user["id"], None, "numerology", free, paid_html,
                         {**meta, "free": True}, paid)
    saved["free"] = True
    saved["price"] = meta["price"]
    return saved


def h_full_report(user: dict, p: dict) -> dict:
    import astro_split as SP
    import astro_voice as V
    # The confluence engine groups findings with SentenceTransformer
    # embeddings. torch + sentence-transformers are excluded from the default
    # worker image (~2 GB), which made this — the most expensive report we
    # sell — fail outright on the default build. Install a lexical stand-in
    # first so the report is produced either way; it is lower quality, and
    # `semantic_fallback.degraded()` says so.
    try:
        import semantic_fallback
        semantic_fallback.install()
    except Exception:                                    # never block a report
        pass
    generate_confluence_reports = None
    if os.getenv("ASTRO_HOTFIX", "1") == "1":
        try:
            import astro_hotfix
            generate_confluence_reports = (
                astro_hotfix.confluence_remedy_fix().generate_confluence_reports)
        except Exception as exc:                                  # noqa: BLE001
            print(f"[handlers] confluence remedy patch unavailable: "
                  f"{type(exc).__name__}: {exc}", flush=True)
    if generate_confluence_reports is None:
        from vedic_confluence_report import generate_confluence_reports

    chart = get_or_create_chart(user["id"], p)
    pc = precompute_for(chart)
    ctx = _voice_ctx(pc, chart)

    work = Path(tempfile.mkdtemp(prefix="rep_"))
    slug = (chart.get("person_name") or "chart").replace(" ", "_")[:24] + "_" + str(chart["id"])[:6]
    pc_path = work / "precomputed.json"
    pc_path.write_text(json.dumps(pc, default=str), encoding="utf-8")

    # Build the twelve specialist lane reports FIRST. Without them the
    # confluence found 0/12 on disk, capped its own confidence at MODERATE and
    # printed a red "Partial pass" banner to the customer. They cost ~0.5s
    # against a warm precompute — the flagship was running thin for nothing.
    try:
        import lane_builder
        lanes = lane_builder.build_lanes(
            work, slug=slug, client_name=chart.get("person_name") or "Seeker",
            dob=str(chart["dob"]), birth_time=str(chart["tob"]),
            latitude=float(chart["lat"]), longitude=float(chart["lon"]),
            timezone=float(chart["tz_offset"]),
            place_name=chart.get("place") or "",
            gender=gender_code(chart.get("gender")),
            precomputed_path=str(pc_path), budget_seconds=240)
    except Exception as exc:                        # never block the report
        print(f"[full_report] lane build failed entirely: {exc}", flush=True)
        lanes = {"built": [], "failed": {"all": str(exc)}}

    conf_path, user_path, _focus, _payload = generate_confluence_reports(
        "", str(work), chart.get("person_name") or "Seeker", str(chart["dob"]), slug,
        client_question="", precomputed_path=str(pc_path),
        birth_time=str(chart["tob"]), latitude=float(chart["lat"]),
        longitude=float(chart["lon"]), timezone=float(chart["tz_offset"]),
        place_name=chart.get("place") or "", gender=gender_code(chart.get("gender")))

    def _html(value: str) -> str:
        """The generator hands back a path OR the document itself.

        Which one depends on whether it could write to the output directory,
        and the handler assumed "path" — so a 90-second report ended in
        `OSError: File name too long`, the whole HTML document having been
        passed to open(). Both shapes are now accepted.
        """
        if not value:
            return ""
        if "<" in value[:200] or len(value) > 512:
            return value
        f = Path(value)
        return f.read_text(encoding="utf-8", errors="ignore") if f.is_file() else ""

    # ---- what the customer receives ------------------------------------
    # The card design, not the long-form confluence document. The confluence
    # still runs above: it is what the lanes vote into, and it stays available
    # behind the paywall as the analyst view for anyone who wants the workings.
    #
    # Rendered TWICE rather than split, because the paywall now sits inside each
    # card — headline and evidence free, dated window and remedy paid. Splitting
    # a document by headings would either give away the timing or hide the
    # headlines, and it broke whenever a heading was renamed.
    import report_render as RD
    lang = str(p.get("language") or (_payload or {}).get("language") or "en")
    free_html, paid_html, meta = RD.full_report(
        pc, name=chart.get("person_name") or "Seeker",
        price=S.price("full_report") // 100,
        bundle_price=S.price("bundle_all") // 100,
        lat=float(chart["lat"]), lon=float(chart["lon"]),
        tz=float(chart["tz_offset"]),
        lang=lang)
    # Card HTML used to skip the full voice pass that the long-form appendix gets.
    # Phase 1: personalise (local openings + humanise) — no cloud LLM required.
    if str(lang or "").lower() not in (
        "hi_en", "hinglish", "hi", "hindi", "te_en", "tenglish", "te", "telugu"
    ):
        free_html = V.personalise(free_html, ctx, "full_report")
        paid_html = V.personalise(paid_html, ctx, "full_report")
        free_html = V.translate_jargon(free_html, keep_original=False)
        paid_html = V.translate_jargon(paid_html, keep_original=False)

    # The long-form lane document is kept as a clearly-labeled technical
    # appendix, separated from customer prose by a heading and collapsed by
    # default.  The summary text is customer-neutral to avoid internal-data
    # leakage into the visible report.
    try:
        conf = SP.split_confluence(V.personalise(_html(conf_path), ctx, "full_report"))
        raw = conf.get("paid_html", "") or ""
        appendix = RD._appendix_block(raw, summary="Technical details (collapsed)")
        if appendix:
            paid_html += appendix
            meta["paidSections"] = list(meta.get("paidSections", [])) + \
                ["Technical details (collapsed)"]
            meta["semantic_mode"] = (_payload or {}).get("semantic_mode", "")
    except Exception as exc:                                          # noqa: BLE001
        print(f"[full_report] appendix skipped: {type(exc).__name__}: {exc}",
              flush=True)

    meta["lanes"] = {"built": len((lanes or {}).get("built") or []),
                     "failed": list(((lanes or {}).get("failed") or {}).keys())}
    meta["semantic_mode"] = (_payload or {}).get("semantic_mode", "")
    paid = entitled(user["id"], "full_report", chart["id"])
    meta["language"] = lang
    saved = _save_report(user["id"], chart["id"], "full_report",
                         free_html, paid_html, meta, paid)
    saved["chartId"] = chart["id"]
    saved["price"] = meta["price"]
    import shutil
    shutil.rmtree(work, ignore_errors=True)
    return saved


def h_classical_report(user: dict, p: dict) -> dict:
    """Classical Vedic Report — the traditional seven-section reading.

    Deliberately separate from `h_full_report`: no lanes, no confluence and no
    LLM. The chart facts go straight to the book corpora and out through the
    classical boundary, which is what keeps the traditional grammar intact.
    """
    # The horizon scan embeds the book corpus. torch is not in the default
    # worker image, so install the lexical stand-in the same way the flagship
    # report does rather than fail outright.
    try:
        import semantic_fallback
        semantic_fallback.install()
    except Exception:                                    # never block a report
        pass

    from classical_report import classical_report

    chart = get_or_create_chart(user["id"], p)
    pc = precompute_for(chart)

    free_html, paid_html, meta = classical_report(
        pc,
        name=chart.get("person_name") or "Seeker",
        dob=str(chart["dob"]),
        tob=str(chart["tob"]),
        place=chart.get("place") or "",
        price=S.price("classical_report") // 100,
        bundle_price=S.price("bundle_all") // 100,
    )

    paid = entitled(user["id"], "classical_report", chart["id"])
    meta["language"] = p.get("language") or "en"
    saved = _save_report(user["id"], chart["id"], "classical_report",
                         free_html, paid_html, meta, paid)
    saved["chartId"] = chart["id"]
    saved["price"] = meta["price"]
    return saved


def h_horary(user: dict, p: dict) -> dict:
    # Question → house / topic. Optional life-area dropdown pins the domain.
    area = ""
    try:
        import semantic_fallback
        semantic_fallback.install()
    except Exception:
        pass
    try:
        import semantic_question as SQ
        area = SQ.normalize_area(p.get("area") or "")
    except Exception as exc:  # noqa: BLE001
        print(f"[horary] area normalize skipped: {exc}", flush=True)

    # Vedic vs Western: the user can tick "I am also a Vedic customer" or the
    # system can detect it from their past reports.
    vedic_customer = bool(p.get("vedicCustomer"))

    htmls = {}
    verdicts = {}
    western_judgment = None
    try:
        from western_horary_report import generate_western_horary_html as wgen
        qh = None
        if area:
            try:
                from horary_answer import _AREA_TO_HOUSE
                qh = _AREA_TO_HOUSE.get(area)
            except Exception:
                qh = None
        h, j = wgen(p["question"], p["qDate"], p["qTime"],
                    p.get("location", "New Delhi"), quesited_house=qh)
        htmls["western"] = h
        verdicts["western"] = {k: j.get(k) for k in ("verdict", "confidence", "score")}
        western_judgment = j
    except Exception as exc:                                          # noqa: BLE001
        verdicts["western"] = {"error": f"{type(exc).__name__}: {exc}"}
    if not htmls:
        raise RuntimeError("western horary failed: " + json.dumps(verdicts))

    ctx = {"name": user.get("name") or "Seeker", "question": p["question"],
           "asked": f"{p['qDate']} {p['qTime']}", "place": p.get("location", "")}

    paid = entitled(user["id"], "horary")
    if not paid and is_subscribed(user["id"]):
        ok, _ = use_quota(user["id"], "horary", S.sub_horary_per_month, month_period())
        paid = ok

    import report_render as RD
    horary_price = S.price("horary") // 100
    lang = str(p.get("language") or "en")
    free_html, paid_html, hmeta = RD.horary(
        question=p["question"], verdicts=verdicts,
        western_judgment=western_judgment, asked=ctx["asked"],
        name=user.get("name") or "",
        horary_price=horary_price,
        full_report_price=S.price("full_report") // 100,
        vedic_customer=vedic_customer,
        lang=lang)

    meta = {**hmeta, "verdicts": verdicts, "price": horary_price, "language": lang}
    saved = _save_report(user["id"], None, "horary", free_html, paid_html,
                         meta, paid)
    saved["price"] = meta["price"]
    return saved


def h_user_question(user: dict, p: dict) -> dict:
    """Natal-chart question: area dropdown + wording → deep evidence / timing."""
    q = (p.get("question") or "").strip()
    if not q:
        raise UserError("Type your question first.")

    try:
        import semantic_fallback
        semantic_fallback.install()
    except Exception:                                    # never block a report
        pass

    area = ""
    route = None
    try:
        import semantic_question as SQ
        area = SQ.normalize_area(p.get("area") or "")
        route = SQ.route(q, area=area)
        print(f"[user_question] semantic route method={route.method} "
              f"house={route.primary_house} domain={route.domain} "
              f"topic={route.topic} area={area or '-'} "
              f"h_sc={route.house_score:.2f}", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"[user_question] semantic route skipped: {exc}", flush=True)
        area = (p.get("area") or "").strip().lower()

    chart = get_or_create_chart(user["id"], p)
    pc = precompute_for(chart)

    import deep_evidence as DE
    import report_render as RD
    uq_price = S.price("user_question") // 100
    lang = str(p.get("language") or "en")
    DE.begin(pc, lat=float(chart["lat"]), lon=float(chart["lon"]),
             tz=float(chart["tz_offset"]))
    try:
        free_html, paid_html, meta = RD.user_question(
            pc, question=q, route=route, area=area,
            name=chart.get("person_name") or "",
            price=uq_price,
            lat=float(chart["lat"]), lon=float(chart["lon"]),
            tz=float(chart["tz_offset"]),
            lang=lang)
    finally:
        DE.end()

    paid = entitled(user["id"], "user_question", chart["id"])
    meta["language"] = lang
    saved = _save_report(user["id"], chart["id"], "user_question",
                         free_html, paid_html, meta, paid)
    saved["chartId"] = chart["id"]
    saved["price"] = meta["price"]
    return saved


def h_daily(user: dict, p: dict) -> dict:
    import astro_voice as V
    import report_render as RD
    from daily_moon_prediction import compute_daily_moon_guide
    chart = get_or_create_chart(user["id"], p)
    pc = precompute_for(chart)
    target = _as_date(p.get("date") or date.today().isoformat())

    # First `FREE_DAILY` full readings per account, then the working locks until
    # the ₹298/month subscription. Verdict + Moon proof stay in the free half.
    subscribed = entitled(user["id"], "daily")
    trial_left = daily_trial_remaining(user["id"]) if not subscribed else 0
    paid = subscribed or trial_left > 0

    data = compute_daily_moon_guide(pc, target, latitude=float(chart["lat"]),
                                    longitude=float(chart["lon"]),
                                    timezone=float(chart["tz_offset"]))
    if isinstance(data, dict):
        data["personal_note"] = V.concise(V.humanise(V.chart_opening(_voice_ctx(pc, chart)))) \
            .replace("<p>", "").replace("</p>", "")

    free_html, paid_html, meta = RD.daily(
        data if isinstance(data, dict) else {},
        lat=float(chart["lat"]), lon=float(chart["lon"]),
        tz=float(chart["tz_offset"]), day=target,
        name=chart.get("person_name") or p.get("name") or "Seeker",
        price=S.price("subscription") // 100,
        pc=pc)
    saved = _save_report(user["id"], chart["id"], "daily",
                         free_html, paid_html, meta, paid=paid)
    if subscribed:
        pin_subscribed_daily_reports(user["id"])
    trial_left_after = daily_trial_remaining(user["id"]) if not subscribed else 0
    saved.update({
        "locked": not paid,
        "date": target.isoformat(),
        "subscribed": subscribed,
        "dailyTrialLeft": trial_left_after,
        "price": meta["price"],
        "chartId": chart["id"],
    })
    return saved


def h_kundali_match(user: dict, p: dict) -> dict:
    import astro_split as SP
    import astro_voice as V
    from kundali_match import build_person_chart, match_kundali
    from kundali_match_report import write_kundali_match_report

    def person(pre: str) -> dict:
        return {"name": p.get(pre + "Name") or pre.title(), "dob": p[pre + "Dob"],
                "birth_time": p[pre + "Tob"], "latitude": float(p[pre + "Lat"]),
                "longitude": float(p[pre + "Lon"]),
                "timezone": float(p.get(pre + "Tz", 5.5)),
                "place_name": p.get(pre + "Place", ""),
                "gender": 0 if pre == "groom" else 1}

    g, b = person("groom"), person("bride")
    result = match_kundali(groom=build_person_chart(**g), bride=build_person_chart(**b),
                          method=p.get("method", "North"),
                          groom_name=g["name"], bride_name=b["name"],
                          groom_dob=g["dob"], bride_dob=b["dob"])

    work = Path(tempfile.mkdtemp(prefix="match_"))
    out = work / "match.html"
    write_kundali_match_report(
        result=result,
        groom_meta={"name": g["name"], "dob": g["dob"], "tob": g["birth_time"],
                    "place": g["place_name"]},
        bride_meta={"name": b["name"], "dob": b["dob"], "tob": b["birth_time"],
                    "place": b["place_name"]},
        out_path=out)
    html = V.personalise(out.read_text(encoding="utf-8", errors="ignore"),
                         {"name": f"{g['name']} & {b['name']}", "dob": g["dob"],
                          "place": g["place_name"], "tob": g["birth_time"]},
                         "kundali_match")
    split = SP.split_report(html, ("kundali milan", "final verdict", "layer 1",
                                   "ashtakoota", "prepared for"),
                            locked_note="Your guna score is above. Unlock the dosha "
                                        "analysis and its remedies, the Navamsha (D9) "
                                        "synastry and the numerology compatibility.")
    a = result.get("ashtakoota") or {}
    # (meta is assembled below; the card render needs it, so it happens first)
    vd = result.get("verdict") or {}
    doshas = result.get("doshas") or {}
    meta = {"total": a.get("total_guna"), "maxGuna": a.get("max_guna"),
            "band": a.get("band"), "bandPlain": a.get("band_plain"),
            "verdict": vd.get("verdict"), "headline": vd.get("headline"),
            "d9Verdict": vd.get("d9_verdict"),
            "koots": [{"label": k.get("label"), "score": k.get("score"),
                       "max": k.get("max"), "ok": k.get("ok")}
                      for k in (a.get("koots") or [])],
            "stars": {"groom": a.get("groom_nakshatra"), "bride": a.get("bride_nakshatra"),
                      "groomMoon": a.get("groom_moon_sign"),
                      "brideMoon": a.get("bride_moon_sign")},
            "activeDoshas": [d.get("name") for d in (doshas.get("items") or [])
                             if d.get("active")],
            "blocking": doshas.get("has_blocking"),
            "couple": {"groom": g["name"], "bride": b["name"]},
            "paidSections": split["paid_sections"], "teasers": split["teasers"],
            "price": S.price("kundali_match") // 100}
    paid = entitled(user["id"], "kundali_match")

    # Card design. Guna names are translated to what each test actually measures
    # — eight Sanskrit column headings undid the clarity of every other screen.
    # The long-form report stays as the paid appendix.
    import report_render as RD
    free_html, paid_html, cmeta = RD.kundali_match(
        meta, groom=g["name"], bride=b["name"],
        price=S.price("kundali_match") // 100)
    appendix = RD._appendix_block(
        split.get("paid_html", "") or "",
        summary="Full matching report — check the reasoning")
    if appendix:
        paid_html += appendix
    meta = {**meta, **cmeta,
            "paidSections": cmeta["paidSections"] + split["paid_sections"],
            "teasers": split["teasers"]}
    saved = _save_report(user["id"], None, "kundali_match",
                         free_html, paid_html, meta, paid)
    saved["price"] = meta["price"]
    import shutil
    shutil.rmtree(work, ignore_errors=True)
    return saved


def h_muhurat_events(user: dict, p: dict) -> dict:
    from muhurat_checker import event_catalog
    return {"events": event_catalog()}


def h_muhurat(user: dict, p: dict) -> dict:
    import report_render as RD
    from muhurat_checker import check_muhurat
    pc: dict = {}
    chart_id = None
    if p.get("dob") and p.get("tob"):
        chart = get_or_create_chart(user["id"], p)
        chart_id = chart["id"]
        pc = precompute_for(chart)
    res = check_muhurat(event_id=p["eventId"], target=_as_date(p["date"]), pc=pc,
                        latitude=float(p.get("lat", 28.6)),
                        longitude=float(p.get("lon", 77.2)),
                        timezone=float(p.get("tz", 5.5)),
                        place_name=p.get("place", "BirthPlace"),
                        suggest_alternatives=True)
    paid = entitled(user["id"], "muhurat")
    summary = {k: res.get(k) for k in ("available", "error", "verdict", "headline",
                                       "summary", "event_label", "event_plain",
                                       "target_date", "needs_partner_chart")}
    summary["checkCount"] = len(res.get("checks") or [])
    summary["alternativeCount"] = len(res.get("alternatives") or [])
    detail = {k: res.get(k) for k in ("checks", "chart_notes", "panchang",
                                      "day_windows", "alternatives")}
    free_html, paid_html, meta = RD.muhurat(
        summary, detail, price=S.price("muhurat") // 100,
        event_id=p["eventId"], date_str=str(p["date"]))
    saved = _save_report(user["id"], chart_id, "muhurat",
                         free_html, paid_html, meta, paid)
    saved["price"] = meta["price"]
    saved["date"] = p["date"]
    saved["eventId"] = p["eventId"]
    saved["chartId"] = chart_id
    return saved


def h_btr(user: dict, p: dict) -> dict:
    import report_render as RD
    from btr_rectify import rectify_birth_time
    raw = p.get("events") or {}
    if isinstance(raw, list):
        # [{"date": ..., "type": ...}] — what an API client writes without
        # reading the form. The site posts {event_name: date}.
        raw = {e.get("type") or e.get("event") or f"event{i}": e.get("date")
               for i, e in enumerate(raw) if isinstance(e, dict)}
    fields = {(k[4:] if k.startswith("btr_") else k): v
              for k, v in raw.items() if v}
    res = rectify_birth_time(
        client_name=p.get("name", "Seeker"), dob=p["dob"], birth_time=p["tob"],
        latitude=float(p["lat"]), longitude=float(p["lon"]),
        timezone=float(p.get("tz", 5.5)), place_name=p.get("place", ""),
        gender=gender_code(p.get("gender")), event_fields=fields,
        custom_events=p.get("customEvents", ""), auto_apply=False)
    paid = entitled(user["id"], "btr")
    off = res.get("offset_minutes")
    lt, lb = str(res.get("lagna_trial") or ""), str(res.get("lagna_best") or "")
    # Full result for the HTML renderer (paid half includes the corrected time).
    card = {
        "skipped": res.get("skipped"), "reason": res.get("reason"),
        "trialTime": res.get("trial_time"), "confidence": res.get("confidence"),
        "eventsUsed": res.get("events_used"),
        "trialScore": res.get("trial_score"), "bestScore": res.get("best_score"),
        "trialVerdict": res.get("trial_verdict"), "lagnaTrial": res.get("lagna_trial"),
        "changesLagna": bool(lt and lb and lt.split()[0] != lb.split()[0]),
        "movesBy": (None if off is None else
                    ("under a minute" if abs(off) < 1 else
                     f"about {abs(int(off))} minute{'s' if abs(int(off)) != 1 else ''}")),
        "fineScanUsed": res.get("fine_scan_used"),
        "suggestedTime": res.get("suggested_time"),
        "lagnaBest": res.get("lagna_best"),
        "offsetMinutes": off,
        "message": res.get("message"),
    }
    if card.get("skipped"):
        return {"paid": paid, "skipped": True, "reason": card.get("reason"),
                "price": S.price("btr") // 100}
    free_html, paid_html, meta = RD.btr(card, price=S.price("btr") // 100)
    saved = _save_report(user["id"], None, "btr", free_html, paid_html, meta, paid)
    saved["price"] = meta["price"]
    # Public JSON keeps the free-side facts for any legacy client; the
    # corrected time stays only in the paid HTML document.
    saved.update({
        "skipped": False,
        "trialTime": card["trialTime"], "confidence": card["confidence"],
        "eventsUsed": card["eventsUsed"],
        "trialScore": card["trialScore"], "bestScore": card["bestScore"],
        "trialVerdict": card["trialVerdict"], "lagnaTrial": card["lagnaTrial"],
        "changesLagna": card["changesLagna"], "movesBy": card["movesBy"],
        "fineScanUsed": card["fineScanUsed"],
    })
    return saved


def h_future_event(user: dict, p: dict) -> dict:
    from future_event_timing import predict_next_event
    chart = get_or_create_chart(user["id"], p)
    res = predict_next_event(
        client_name=chart.get("person_name") or "Seeker", dob=str(chart["dob"]),
        birth_time=str(chart["tob"]), latitude=float(chart["lat"]),
        longitude=float(chart["lon"]), timezone=float(chart["tz_offset"]),
        place_name=chart.get("place") or "", gender=gender_code(chart.get("gender")),
        event_type=p["eventType"], consultation_date=p.get("consultationDate", ""))
    paid = entitled(user["id"], "future_event")
    return {"paid": paid, "eventType": p["eventType"],
            "promised": res.get("promised"), "timingAvailable": res.get("timing_available"),
            "window": res.get("next_window") if paid else None,
            "alternates": res.get("alternates") if paid else None,
            "remedies": res.get("remedies") if paid else None,
            "error": res.get("error"), "price": S.price("future_event") // 100}


HANDLERS = {
    "palm": h_palm,
    "chart_summary": h_chart_summary,
    "numerology": h_numerology,
    "full_report": h_full_report,
    "classical_report": h_classical_report,
    "user_question": h_user_question,
    "horary": h_horary,
    "daily": h_daily,
    "kundali_match": h_kundali_match,
    "muhurat": h_muhurat,
    "muhurat_events": h_muhurat_events,
    "btr": h_btr,
    "future_event": h_future_event,
}

# Kinds whose result is small JSON and fast enough to run inline in the API
# when the queue is empty. Everything else always goes through a worker.
FAST_KINDS = {"muhurat_events"}
