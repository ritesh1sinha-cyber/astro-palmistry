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

from .billing import (entitled, is_subscribed, month_period, quota_left,
                      use_quota)
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
        free_html, paid_html, meta = build_palm_html_reading(raw_result, p)
        meta = {**meta, "overlays": overlays,
                "price": S.price("palm_full") // 100}
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
        "personalNote": V.humanise(V.chart_opening(_voice_ctx(pc, chart))),
    }


def h_numerology(user: dict, p: dict) -> dict:
    """Six numbers, the Lo Shu grid, this year free and the cycle ahead locked.

    Was `numerology_report.generate_numerology_html`, which produced three
    numbers and no grid. `report_render.numerology` is the card design: Chaldean
    values (the system Indian numerology actually uses), a personal year running
    birthday to birthday, and the Lo Shu grid — the only picture in numerology,
    and the thing that makes people ask why four of their cells are empty.
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
        client_question=p.get("question", ""), precomputed_path=str(pc_path),
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
    free_html, paid_html, meta = RD.full_report(
        pc, name=chart.get("person_name") or "Seeker",
        question=p.get("question", ""),
        price=S.price("full_report") // 100,
        bundle_price=S.price("bundle_all") // 100,
        lat=float(chart["lat"]), lon=float(chart["lon"]),
        tz=float(chart["tz_offset"]))

    # The old long-form document is kept as an appendix on the paid side. It is
    # genuinely useful to the minority who want to check the reasoning, and
    # throwing away a 90-second computation would be wasteful.
    try:
        conf = SP.split_confluence(V.personalise(_html(conf_path), ctx, "full_report"))
        # Through the chokepoint: appending after the render bypassed it, and
        # the old document names a lane "Longevity".
        appendix = RD.clean(conf.get("free_html", "") + conf.get("paid_html", ""))
        if appendix:
            paid_html += ('<hr/><h3 class="sec">The full analyst working</h3>'
                          '<p class="sec-note">Every lane, in full, for anyone who '
                          'wants to check the reasoning.</p>' + appendix)
            meta["paidSections"] = list(meta.get("paidSections", [])) + \
                conf.get("paid_sections", [])
    except Exception as exc:                                          # noqa: BLE001
        print(f"[full_report] appendix skipped: {type(exc).__name__}: {exc}",
              flush=True)

    meta["lanes"] = {"built": len((lanes or {}).get("built") or []),
                     "failed": list(((lanes or {}).get("failed") or {}).keys())}
    paid = entitled(user["id"], "full_report", chart["id"])
    saved = _save_report(user["id"], chart["id"], "full_report",
                         free_html, paid_html, meta, paid)
    saved["chartId"] = chart["id"]
    saved["price"] = meta["price"]
    import shutil
    shutil.rmtree(work, ignore_errors=True)
    return saved


def h_horary(user: dict, p: dict) -> dict:
    import astro_split as SP
    import astro_voice as V

    htmls, verdicts = {}, {}
    western_judgment: dict = {}
    vgen = None
    if os.getenv("ASTRO_HOTFIX", "1") == "1":
        try:
            import astro_hotfix
            vgen = astro_hotfix.horary_glyph_fix().generate_vedic_horary_html
        except Exception as exc:                                      # noqa: BLE001
            # never silent: if the upstream glyph bug is unpatched, Vedic horary
            # dies and the customer silently gets half a product
            print(f"[handlers] horary hotfix unavailable: {type(exc).__name__}: {exc}",
                  flush=True)
            vgen = None
    if vgen is None:
        from vedic_horary_report import generate_vedic_horary_html as vgen
    try:
        h, j = vgen(p["question"], p["qDate"], p["qTime"],
                    p.get("location", "Hyderabad"), p.get("kpNumber", ""))
        htmls["vedic"] = h
        verdicts["vedic"] = {k: j.get(k) for k in ("verdict", "confidence", "score", "systems")}
    except Exception as exc:                                          # noqa: BLE001
        verdicts["vedic"] = {"error": f"{type(exc).__name__}: {exc}"}
    try:
        from western_horary_report import generate_western_horary_html as wgen
        h, j = wgen(p["question"], p["qDate"], p["qTime"], p.get("location", "Hyderabad"))
        htmls["western"] = h
        verdicts["western"] = {k: j.get(k) for k in ("verdict", "confidence")}
        western_judgment = j
    except Exception as exc:                                          # noqa: BLE001
        verdicts["western"] = {"error": f"{type(exc).__name__}: {exc}"}
    if not htmls:
        raise RuntimeError("both horary engines failed: " + json.dumps(verdicts))

    ctx = {"name": user.get("name") or "Seeker", "question": p["question"],
           "asked": f"{p['qDate']} {p['qTime']}", "place": p.get("location", "")}
    splits = {k: SP.split_horary(V.personalise(v, ctx, "horary")) for k, v in htmls.items()}

    paid = entitled(user["id"], "horary")
    if not paid and is_subscribed(user["id"]):
        ok, _ = use_quota(user["id"], "horary", S.sub_horary_per_month, month_period())
        paid = ok

    paid_sections, teasers = [], {}
    for tag, sp in splits.items():
        paid_sections += [f"{tag.title()}: {t}" for t in sp["paid_sections"]]
        teasers.update({f"{tag.title()}: {k}": v for k, v in sp["teasers"].items()})

    # ONE answer, not two engines arguing. Western 60 / Vedic 40; on a genuine
    # contradiction Western's direction wins and confidence drops to low. The
    # per-engine workings sit behind the paywall for anyone who wants to check
    # them — they no longer LEAD with a disagreement, which read as us not
    # knowing rather than as intellectual honesty.
    import report_render as RD
    free_html, paid_html, hmeta = RD.horary(
        question=p["question"], verdicts=verdicts,
        western_judgment=western_judgment, asked=ctx["asked"],
        name=user.get("name") or "", price=S.price("full_report") // 100,
        workings={k: s["free_html"] + s["paid_html"] for k, s in splits.items()})

    meta = {**hmeta, "verdicts": verdicts,
            "paidSections": hmeta.get("paidSections", []) + paid_sections,
            "teasers": teasers, "price": S.price("horary") // 100}
    saved = _save_report(user["id"], None, "horary", free_html, paid_html,
                         meta, paid)
    saved["price"] = meta["price"]
    return saved


def h_daily(user: dict, p: dict) -> dict:
    import astro_voice as V
    import report_render as RD
    from daily_moon_prediction import compute_daily_moon_guide
    chart = get_or_create_chart(user["id"], p)
    pc = precompute_for(chart)
    target = _as_date(p.get("date") or date.today().isoformat())

    subscribed = entitled(user["id"], "daily")
    if not subscribed:
        left = quota_left(user["id"], "daily_free", S.free_daily_readings, "all")
        if left <= 0:
            return {"locked": True, "price": S.price("subscription") // 100,
                    "message": "Your free daily readings are used. "
                               "Subscribe for a reading built from your chart every morning."}
        use_quota(user["id"], "daily_free", S.free_daily_readings, "all")

    data = compute_daily_moon_guide(pc, target, latitude=float(chart["lat"]),
                                    longitude=float(chart["lon"]),
                                    timezone=float(chart["tz_offset"]))
    if isinstance(data, dict):
        data["personal_note"] = V.humanise(V.chart_opening(_voice_ctx(pc, chart))) \
            .replace("<p>", "").replace("</p>", "")

    free_html, paid_html, meta = RD.daily(
        data if isinstance(data, dict) else {},
        lat=float(chart["lat"]), lon=float(chart["lon"]),
        tz=float(chart["tz_offset"]), day=target,
        name=chart.get("person_name") or p.get("name") or "Seeker",
        price=S.price("subscription") // 100)
    # Daily access is quota/subscription; store the card so the site iframes it.
    saved = _save_report(user["id"], chart["id"], "daily",
                         free_html, paid_html, meta, paid=True)
    saved.update({
        "locked": False,
        "date": target.isoformat(),
        "subscribed": subscribed,
        "freeDaysLeft": quota_left(user["id"], "daily_free",
                                   S.free_daily_readings, "all"),
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
    appendix = RD.clean(split.get("free_html", "") + split.get("paid_html", ""))
    if appendix:
        paid_html += ('<hr/><h3 class="sec">The full matching report</h3>'
                      + appendix)
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
