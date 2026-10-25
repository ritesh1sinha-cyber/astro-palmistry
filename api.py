#!/usr/bin/env python3
"""
api.py — the public HTTP surface. Stateless: run as many replicas as you like.

It never runs an engine. Every reading is enqueued to Redis and executed by a
worker, so an API replica needs neither mediapipe nor PyJHora installed and a
slow reading can never block a request thread.

    uvicorn api:app --host 0.0.0.0 --port 8080
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from html import escape as _html_escape
import time
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from core import billing, promo, queue as Q, turnstile as TS
from core.auth import (COOKIE, current_user, has_full_access, has_full_access_id,
                       is_admin, login_admin, login_dev, login_with_google, logout)
from core.config import S
from core.db import (chat_append, chat_history, engine, extend_partitions,
                     init_schema, job_get, job_insert, job_update, jdump,
                     new_id, now, report_delete, report_get, reports_for_user,
                     tx)
from core.pdf_export import (entitlement_item_for_kind, html_to_pdf,
                             prepend_summary, report_title, summary_for_pdf,
                             summary_html)
from core.store import store

app = FastAPI(title="GrahaRekha API", version="3.0")
app.add_middleware(CORSMiddleware, allow_origins=S.allowed_origins,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Reports are NEVER mounted as static files. Delivery is /api/file/{token}.


@app.on_event("startup")
def _startup() -> None:
    init_schema()
    extend_partitions()
    try:
        from core.billing import pin_all_subscribed_daily_reports
        pin_all_subscribed_daily_reports()
    except Exception:                                            # noqa: BLE001
        pass
    # Support revocations that must survive a restart: REVOKE_ORDERS=OD-AAAA,OD-BBBB
    # takes back what those orders unlocked. Idempotent; runs before the binder
    # so a revoked order is not re-bound to a report.
    for pid in [p.strip().upper() for p in os.getenv("REVOKE_ORDERS", "").split(",")
                if p.strip()]:
        try:
            o = billing.order_by_public(pid)
            if o:
                n = billing.revoke_order_access(o)
                print(f"[billing] REVOKE_ORDERS {pid}: {n} entitlement(s) revoked",
                      flush=True)
        except Exception as exc:                                  # noqa: BLE001
            print(f"[billing] REVOKE_ORDERS {pid} failed: {exc}", flush=True)
    try:
        from core.billing import bind_orphan_order_grants
        n = bind_orphan_order_grants()
        if n:
            print(f"[billing] bound {n} account-wide order grant(s) to a report",
                  flush=True)
    except Exception:                                            # noqa: BLE001
        pass

    # The launch offer, seeded from config so the cap is an env var and not a
    # deploy. create_code is idempotent by code, so a restart never resets a
    # counter or reopens an exhausted code.
    if S.promo_code:
        try:
            promo.create_code(S.promo_code, item=S.promo_item,
                              max_redemptions=S.promo_max,
                              note="launch offer")
        except Exception:                                            # noqa: BLE001
            pass    # a bad env var must never stop the API from booting

    # Three deployment shapes, one codebase:
    #   * INLINE_WORKER=1 (or no REDIS_URL) → a worker thread inside this
    #     process. One container, no Redis: fine for a laptop or a pilot.
    #   * REDIS_URL set, separate worker containers → the normal production
    #     shape, scaled by worker replicas.
    #   * many API replicas + many workers → same code, Redis coordinates.
    inline = os.getenv("INLINE_WORKER", "1" if not S.redis_url else "0") == "1"
    if inline:
        import threading

        import worker as W

        def _loop():
            while True:
                try:
                    if not W.run_once():
                        time.sleep(0.4)
                except Exception:                                     # noqa: BLE001
                    time.sleep(2)

        for i in range(int(os.getenv("INLINE_WORKER_THREADS", "2"))):
            threading.Thread(target=_loop, name=f"inline-worker-{i}",
                             daemon=True).start()

    print(f"[api] ready env={S.env} db={'postgres' if S.is_postgres else 'sqlite'} "
          f"redis={'yes' if S.redis_url else 'embedded'} inline_worker={inline}",
          flush=True)


# ===========================================================================
# auth
# ===========================================================================
class GoogleIn(BaseModel):
    idToken: str
    turnstileToken: str = ""


class DevIn(BaseModel):
    email: str = "guest@graharekha.co.in"
    name: str = "Guest Seeker"
    passcode: str = ""
    turnstileToken: str = ""


class AdminIn(BaseModel):
    username: str = ""
    email: str = ""          # legacy
    password: str
    turnstileToken: str = ""


def _set_cookie(resp: Response, token: str) -> None:
    resp.set_cookie(COOKIE, token, max_age=S.session_days * 86400, httponly=True,
                    secure=(S.env == "prod"), samesite="lax", path="/")


@app.get("/api/public-config")
def public_config():
    """Non-secret flags the site needs before sign-in (Google Client ID, etc.)."""
    # Chat UI is shown only when CHAT_ENABLED=1, the LLM layer is on, and
    # "chat" is in LLM_TABS. Production leaves CHAT_ENABLED unset.
    chat_enabled = bool(S.llm_tab_enabled("chat"))
    return {
        "googleClientId": S.google_client_id or "",
        "guestLogin": bool(S.dev_login),
        "adminLogin": bool(S.dev_login),
        "brand": "GrahaRekha",
        "razorpayKeyId": S.razorpay_key_id or "",
        "razorpayPaymentButtonId": S.razorpay_payment_button_id or "",
        "turnstileSiteKey": S.turnstile_site_key or "",
        "turnstileRequired": TS.enabled(),
        "llmEnabled": bool(S.llm_enabled),
        "chatEnabled": chat_enabled,
    }


@app.post("/api/auth/google")
def auth_google(body: GoogleIn, request: Request, response: Response):
    user, token = login_with_google(
        body.idToken, ip=request.client.host if request.client else "",
        ua=request.headers.get("user-agent", ""))
    _set_cookie(response, token)
    return {"token": token, "user": _me(user)}


@app.post("/api/auth/dev")
def auth_dev(body: DevIn, request: Request, response: Response):
    TS.require_human(request, token=body.turnstileToken)
    user, token = login_dev(body.email, body.name, passcode=body.passcode,
                            ip=request.client.host if request.client else "",
                            ua=request.headers.get("user-agent", ""))
    _set_cookie(response, token)
    return {"token": token, "user": _me(user)}


@app.post("/api/auth/admin")
def auth_admin(body: AdminIn, request: Request, response: Response):
    TS.require_human(request, token=body.turnstileToken)
    user, token = login_admin(username=body.username, email=body.email,
                              password=body.password,
                              ip=request.client.host if request.client else "",
                              ua=request.headers.get("user-agent", ""))
    _set_cookie(response, token)
    return {"token": token, "user": _me(user)}


@app.post("/api/auth/logout")
def auth_logout(request: Request, response: Response):
    tok = request.cookies.get(COOKIE, "")
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        tok = auth[7:]
    logout(tok)
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


def _me(user: dict) -> dict:
    sub = billing.subscription_of(user["id"])
    subscribed = billing.is_subscribed(user["id"])
    admin = is_admin(user)
    full = has_full_access(user)
    return {"id": user["id"], "email": user["email"], "name": user.get("name"),
            "picture": user.get("picture"), "credits": user.get("credits", 0),
            "admin": admin,
            "fullAccess": full,
            "subscribed": subscribed or full,
            "subUntil": (sub or {}).get("current_period_end"),
            "horaryLeft": (999 if full else
                           (billing.quota_left(user["id"], "horary",
                                               S.sub_horary_per_month,
                                               billing.month_period())
                            if subscribed else 0)),
            "dailyTrialLeft": (billing.daily_trial_remaining(user["id"])
                               if not (subscribed or full) else 0),
            "generationsLeftToday": (billing.report_gen_remaining(user["id"])
                                     if subscribed and not full else None),
            "generationsAllowanceToday": (billing.report_gen_allowance(user["id"])
                                          if subscribed and not full else None)}


@app.get("/api/me")
def me(user: dict = Depends(current_user)):
    return _me(user)


@app.get("/api/admin/report-stats")
def admin_report_stats(user: dict = Depends(current_user)):
    """Global free-report counts per section — admin only."""
    if not is_admin(user):
        raise HTTPException(403, "admin only")
    from core.stats import get_report_generation_counts
    return {"counts": get_report_generation_counts()}


@app.get("/api/admin/analysis")
def admin_analysis(user: dict = Depends(current_user)):
    """Free reports, paid orders, and page views — admin only."""
    if not is_admin(user):
        raise HTTPException(403, "admin only")
    from core.stats import admin_analysis_summary
    return admin_analysis_summary()


@app.get("/api/admin/enquiries")
def admin_enquiries_list(status: str = "", limit: int = 50,
                         user: dict = Depends(current_user)):
    """Contact-form submissions — admin only."""
    if not is_admin(user):
        raise HTTPException(403, "admin only")
    from core.enquiries import list_enquiries
    try:
        return list_enquiries(status=status, limit=limit)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


class EnquiryStatusIn(BaseModel):
    status: str


@app.patch("/api/admin/enquiries/{enquiry_id}")
def admin_enquiry_status(enquiry_id: str, body: EnquiryStatusIn,
                         user: dict = Depends(current_user)):
    """Mark an enquiry new / replied / closed — admin only."""
    if not is_admin(user):
        raise HTTPException(403, "admin only")
    from core.enquiries import set_enquiry_status
    try:
        return set_enquiry_status(enquiry_id, body.status)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


class PageViewIn(BaseModel):
    path: str = ""


@app.post("/api/analytics/pageview")
def record_pageview(body: PageViewIn):
    """Public, fire-and-forget SPA view counter (whitelist only)."""
    from core.stats import increment_page_view
    ok = increment_page_view(body.path or "")
    if not ok:
        raise HTTPException(400, "unknown path")
    return {"ok": True}


# ===========================================================================
# jobs
# ===========================================================================
class JobIn(BaseModel):
    kind: str
    payload: dict = Field(default_factory=dict)
    turnstileToken: str = ""


@app.post("/api/job")
def submit_job(body: JobIn, request: Request, user: dict = Depends(current_user)):
    from core.handlers import HANDLERS
    TS.require_human(request, token=body.turnstileToken)
    public_kinds = sorted(k for k in HANDLERS if not k.startswith("admin_"))
    if body.kind not in public_kinds:          # admin_* kinds are queued by admin endpoints only
        raise HTTPException(400, f"unknown kind; try {public_kinds}")
    # One job at a time per login: a second tap while the first is still
    # queued or running is refused before it can use up a daily slot.
    if Q.has_active_job(str(user["id"])):
        raise HTTPException(
            429,
            "Your previous report is still being prepared. "
            "Please wait for it to finish before starting another.")
    allowed, _remaining, allowance = billing.check_report_generation(
        user["id"], body.kind)
    if not allowed:
        raise HTTPException(
            429,
            f"Daily report limit reached ({allowance} per IST day, "
            f"resets at midnight IST). Purchase a report today for one extra slot, "
            f"or try again tomorrow.",
        )
    if body.kind in billing.GENERATION_LIMIT_KINDS:
        ok, _left = billing.consume_report_generation(user["id"])
        if not ok:
            raise HTTPException(
                429,
                "Daily report limit reached — resets at midnight IST.",
            )
    if not Q.rate_ok(user["id"]):
        raise HTTPException(429, "too many requests — slow down a moment")
    if Q.total_depth() > S.max_queue_depth:
        raise HTTPException(503, "we are at capacity — please try again shortly")

    # paying and subscribed users get ahead of the free queue
    ref = body.payload.get("chartId") or body.payload.get("reportId")
    paid = billing.entitled(user["id"], body.kind, ref) if body.kind in S.prices else False
    priority = Q.priority_for(paid=paid, subscribed=billing.is_subscribed(user["id"]))

    job = Q.enqueue(kind=body.kind, user_id=user["id"], payload=body.payload,
                    priority=priority)
    Q.mark_active(str(user["id"]), job["jobId"])
    job_insert(public_id=job["jobId"], user_id=user["id"], kind=body.kind,
               payload=body.payload, priority=priority)
    return JSONResponse(Q.snapshot(job))


@app.get("/api/job/{pid}")
def job_status(pid: str, user: dict = Depends(current_user)):
    job = Q.load(pid)
    uid = str(user["id"])
    if job is None:                                   # fell out of Redis TTL
        row = job_get(pid)
        if not row or str(row.get("user_id")) != uid:
            raise HTTPException(404, "no such job")
        return {"jobId": pid, "kind": row["kind"], "status": row["status"],
                "queuePosition": 0, "etaSeconds": 0,
                "error": row.get("error"), "result": None,
                "note": "this job has expired from the live queue"}
    if str(job.get("userId")) != uid:
        raise HTTPException(404, "no such job")
    snap = Q.snapshot(job)
    snap["result"] = _decorate(snap.get("result"), user["id"], kind=snap.get("kind") or "")
    return JSONResponse(snap)


@app.delete("/api/job/{pid}")
def job_cancel(pid: str, user: dict = Depends(current_user)):
    job = Q.load(pid)
    if not job or str(job.get("userId")) != str(user["id"]):
        raise HTTPException(404, "no such job")
    ok = Q.cancel(pid)
    if ok:
        job_update(pid, status="cancelled", finished_at=now())
    return {"ok": ok}


# ===========================================================================
# reports + signed delivery
# ===========================================================================
def _sign(payload: str) -> str:
    return hmac.new(S.secret.encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]


def file_token(report_id: str, half: str, user_id: str) -> str:
    exp = int(time.time()) + S.link_ttl_seconds
    body = f"{report_id}.{half}.{user_id}.{exp}"
    return f"{body}.{_sign(body)}"


def _links(rid: str, uid: str, paid: bool) -> dict:
    unlocked = paid or has_full_access_id(uid)
    out = {"free": f"/api/file/{file_token(rid, 'free', uid)}"}
    if unlocked:
        out["paid"] = f"/api/file/{file_token(rid, 'paid', uid)}"
    return out


def _owns_report(rep: dict, uid: str) -> bool:
    """Ownership, never payment.

    ``_report_unlocked`` answers "may this half be shown at all", and it says
    yes for every paid row — so it can never stand in for an ownership check.
    Reading one as the other hands any signed-in reader somebody else's chart.
    """
    return str(rep.get("user_id")) == str(uid) or has_full_access_id(uid)


def _report_unlocked(rep: dict, uid: str) -> bool:
    if bool(rep.get("paid")) or has_full_access_id(uid):
        return True
    # Order may have granted the item even if reports.paid lagged.
    try:
        kind = rep.get("kind") or ""
        item = entitlement_item_for_kind(kind)
        if item and billing.entitled(uid, item, rep.get("id")):
            return True
        if item and billing.entitled(uid, item, None):
            return True
        # Subscription covers daily / muhurat / horary even without a row flag.
        if kind in ("daily", "muhurat", "horary") and billing.is_subscribed(uid):
            return True
    except Exception:                                                 # noqa: BLE001
        pass
    return False


_LOCKED_KINDS = frozenset({"horary", "user_question"})


def _gate_meta(kind: str, meta: dict, unlocked: bool) -> dict:
    """Strip paid-only fields from JSON when the report is still locked."""
    if unlocked or not isinstance(meta, dict):
        return meta
    # plainSummaryPaid summarises the paid half for every kind, so it is gated
    # for every kind — not only the ones that hide a verdict.
    out = {**meta, "plainSummaryPaid": None}
    if kind in _LOCKED_KINDS:
        out.update({"answer": None, "verdicts": {}})
    return out


@app.get("/api/file/{token}")
def serve_file(token: str):
    try:
        rid, half, uid, exp, sig = token.rsplit(".", 4)
    except ValueError:
        raise HTTPException(400, "malformed link")
    if not hmac.compare_digest(sig, _sign(f"{rid}.{half}.{uid}.{exp}")):
        raise HTTPException(403, "invalid link")
    if int(exp) < time.time():
        raise HTTPException(410, "this link has expired — reopen the report")
    rep = report_get(rid)
    if not rep:
        raise HTTPException(404, "no such report")
    if not _owns_report(rep, uid):
        raise HTTPException(403, "not authorized")
    if half == "paid" and not _report_unlocked(rep, uid):
        raise HTTPException(402, "payment required")
    key = rep["paid_key"] if half == "paid" else rep["free_key"]
    if not key:
        raise HTTPException(404, "nothing stored for that half")
    try:
        data = store().get(key)
    except Exception:                                                 # noqa: BLE001
        print(f"[api] STORED REPORT MISSING report={rid} half={half} key={key}",
              flush=True)
        if key.endswith(".json"):
            raise HTTPException(404, "the stored report is missing")
        # This is shown inside the report frame, so say what happened and what
        # to do rather than a bare JSON error.
        return Response(
            status_code=404, media_type="text/html; charset=utf-8",
            content=("<!doctype html><meta charset=utf-8>"
                     "<body style='font-family:system-ui,sans-serif;max-width:480px;"
                     "margin:48px auto;padding:0 20px;color:#222;line-height:1.5'>"
                     "<h2>This report needs to be restored</h2>"
                     "<p>Your payment and access are safe, but the saved copy of this "
                     "report could not be found on our server. Please write to us "
                     "with this reference and we will re-send it to you: "
                     f"<b>{_html_escape(str(rid)[:8].upper())}</b>.</p></body>"))
    media = "application/json" if key.endswith(".json") else "text/html; charset=utf-8"
    return Response(content=data, media_type=media,
                    headers={"Cache-Control": "private, max-age=300"})


def obj_token(key: str, user_id: str) -> str:
    exp = int(time.time()) + S.link_ttl_seconds
    body = f"{key}|{user_id}|{exp}"
    return f"{body}|{_sign(body)}"


@app.get("/api/obj/{token:path}")
def serve_object(token: str):
    """Serve a stored object (e.g. a palm overlay) under a signed, expiring URL."""
    try:
        key, uid, exp, sig = token.rsplit("|", 3)
    except ValueError:
        raise HTTPException(400, "malformed link")
    if not hmac.compare_digest(sig, _sign(f"{key}|{uid}|{exp}")):
        raise HTTPException(403, "invalid link")
    if int(exp) < time.time():
        raise HTTPException(410, "this link has expired")
    if not key.startswith(("overlays/", "reports/")):
        raise HTTPException(403, "not a servable object")
    try:
        data = store().get(key)
    except Exception:                                                 # noqa: BLE001
        raise HTTPException(404, "not found")
    media = ("image/jpeg" if key.endswith((".jpg", ".jpeg"))
             else "image/png" if key.endswith(".png")
             else "application/json" if key.endswith(".json") else "text/html")
    return Response(content=data, media_type=media,
                    headers={"Cache-Control": "private, max-age=600"})


def _decorate(result: Any, uid: str, kind: str = "") -> Any:
    """Turn storage keys in a job result into signed, expiring URLs."""
    if not isinstance(result, dict):
        return result
    if isinstance(result.get("overlays"), dict):
        result["overlays"] = {k: f"/api/obj/{obj_token(v, uid)}"
                              for k, v in result["overlays"].items()
                              if isinstance(v, str)}
    rid = result.get("reportId")
    unlocked = bool(result.get("paid")) or has_full_access_id(uid)
    if rid and "links" not in result:
        result["links"] = _links(rid, uid, unlocked)
    if isinstance(result.get("meta"), dict):
        result["meta"] = _gate_meta(kind, result["meta"], unlocked)
    return result


@app.get("/api/reports")
def my_reports(paid: Optional[int] = None, user: dict = Depends(current_user)):
    """List the caller's reports. Pass paid=1 for unlocked/purchased only."""
    out = []
    for r in reports_for_user(user["id"]):
        unlocked = _report_unlocked(r, user["id"])
        if paid and not unlocked:
            continue
        meta = _gate_meta(r["kind"], r["meta"], unlocked)
        out.append({"reportId": r["id"], "kind": r["kind"],
                    "paid": unlocked,
                    "title": report_title(r["kind"], r.get("meta") or {}),
                    "createdAt": r["created_at"],
                    "meta": meta,
                    "links": _links(r["id"], user["id"], unlocked)})
    return out


@app.get("/api/reports/{rid}")
def one_report(rid: str, user: dict = Depends(current_user)):
    rep = report_get(rid)
    if not rep or not _owns_report(rep, user["id"]):
        raise HTTPException(404, "no such report")
    unlocked = _report_unlocked(rep, user["id"])
    return {"reportId": rep["id"], "kind": rep["kind"], "paid": unlocked,
            "title": report_title(rep["kind"], rep.get("meta") or {}),
            "meta": _gate_meta(rep["kind"], rep["meta"], unlocked),
            "links": _links(rid, user["id"], unlocked)}


def _pdf_response(pdf: bytes, fname: str) -> Response:
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{fname}"',
            "Cache-Control": "private, no-store",
        },
    )


def _pdf_bytes(html: str) -> bytes:
    try:
        return html_to_pdf(html)
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except Exception as e:                                            # noqa: BLE001
        # Surface a short hint; full traceback is in Railway logs via pdf_export.
        hint = (str(e) or type(e).__name__)[:160]
        raise HTTPException(500, f"could not build the PDF ({hint})")


def _pdf_name(rep: dict, suffix: str = "") -> str:
    kind = (rep.get("kind") or "report").replace("_", "-")
    created = str(rep.get("created_at") or "")[:10] or "report"
    return f"graharekha-{kind}{suffix}-{created}.pdf"


def _report_summary(rep: dict, unlocked: bool) -> Optional[dict]:
    """The summary this reader may download, chosen through the same gate as JSON."""
    kind = rep.get("kind") or ""
    meta = _gate_meta(kind, rep.get("meta") or {}, unlocked)
    return summary_for_pdf(meta, unlocked=unlocked)


@app.get("/api/reports/{rid}/pdf")
def report_pdf(rid: str, summary: bool = True, user: dict = Depends(current_user)):
    """Download the paid HTML half as a PDF. Locked reports → 402.

    The plain-English summary rides along as the first page unless the caller
    passes summary=0 — most readers want the crux before the detail.
    """
    rep = report_get(rid)
    if not rep or not _owns_report(rep, user["id"]):
        raise HTTPException(404, "no such report")
    if not _report_unlocked(rep, user["id"]):
        raise HTTPException(402, "payment required")
    key = rep.get("paid_key") or ""
    if not key:
        raise HTTPException(404, "nothing stored for that half")
    try:
        data = store().get(key)
    except Exception:                                                 # noqa: BLE001
        raise HTTPException(404, "the stored report is missing")
    if key.endswith(".json"):
        raise HTTPException(415, "this older report cannot be exported as PDF")
    html = data.decode("utf-8", errors="replace")
    if summary:
        brief = _report_summary(rep, True)
        if brief:
            html = prepend_summary(html, summary_html(
                brief,
                title=report_title(rep.get("kind") or "", rep.get("meta") or {}),
                subtitle=str(rep.get("created_at") or "")[:10],
                language=str(brief.get("language") or (rep.get("meta") or {}).get("language") or "en"),
            ))
    return _pdf_response(_pdf_bytes(html), _pdf_name(rep))


@app.get("/api/reports/{rid}/summary.pdf")
def report_summary_pdf(rid: str, user: dict = Depends(current_user)):
    """Download just the plain-English summary of a report.

    A locked report yields its free summary — that half is already on screen,
    so there is nothing to withhold, and it is the shareable page.
    """
    rep = report_get(rid, user["id"])
    if not rep:
        raise HTTPException(404, "no such report")
    unlocked = _report_unlocked(rep, user["id"])
    brief = _report_summary(rep, unlocked)
    if not brief:
        raise HTTPException(404, "no summary stored for that report")
    doc = summary_html(
        brief,
        title=report_title(rep.get("kind") or "", rep.get("meta") or {}),
        subtitle=str(rep.get("created_at") or "")[:10],
        standalone=True,
        language=str(brief.get("language") or (rep.get("meta") or {}).get("language") or "en"),
    )
    return _pdf_response(_pdf_bytes(doc), _pdf_name(rep, "-summary"))


@app.delete("/api/reports/{rid}")
def delete_one_report(rid: str, user: dict = Depends(current_user)):
    """Remove a report from the caller's history (DB row + free/paid objects)."""
    rep = report_get(rid, user["id"])
    if not rep:
        raise HTTPException(404, "no such report")
    st = store()
    for k in (rep.get("free_key"), rep.get("paid_key"),
              (rep.get("meta") or {}).get("facts_key")):
        if not k:
            continue
        try:
            st.delete(k)
        except Exception:                                             # noqa: BLE001
            pass
    if not report_delete(rid, user["id"]):
        raise HTTPException(404, "no such report")
    return {"ok": True, "reportId": rid}


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=1200)


def _require_chat_enabled() -> None:
    """Chat needs CHAT_ENABLED=1 on top of the LLM layer and the tab list."""
    if not S.llm_tab_enabled("chat"):
        raise HTTPException(
            503,
            "report chat is disabled — set CHAT_ENABLED=1 with LLM_ENABLED=1 "
            "and chat in LLM_TABS",
        )


@app.get("/api/reports/{rid}/chat")
def report_chat_history(rid: str, user: dict = Depends(current_user)):
    """Return recent chat turns for a paid report."""
    _require_chat_enabled()
    rep = report_get(rid)
    if not rep or not _owns_report(rep, user["id"]):
        raise HTTPException(404, "no such report")
    if not _report_unlocked(rep, user["id"]):
        raise HTTPException(402, "payment required")
    return {"reportId": rid, "messages": chat_history(rid, user["id"], limit=40)}


@app.post("/api/reports/{rid}/chat")
def report_chat(rid: str, body: ChatIn, user: dict = Depends(current_user)):
    """Paid-only follow-up chat grounded in the report's facts.json.

    Never invents predictions outside the persisted facts. Rate-limited.
    """
    _require_chat_enabled()
    rep = report_get(rid)
    if not rep or not _owns_report(rep, user["id"]):
        raise HTTPException(404, "no such report")
    if not _report_unlocked(rep, user["id"]):
        raise HTTPException(402, "payment required")
    if not Q.rate_ok(user["id"]):
        raise HTTPException(429, "too many requests — try again in a moment")

    meta = rep.get("meta") or {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except Exception:                                             # noqa: BLE001
            meta = {}
    facts_key = meta.get("facts_key") or ""
    facts: Any = {}
    if facts_key:
        try:
            facts = json.loads(store().get(facts_key).decode("utf-8"))
        except Exception:                                             # noqa: BLE001
            facts = {}
    if not facts:
        raise HTTPException(
            503,
            "this report has no fact context for chat yet — regenerate it with "
            "the LLM layer enabled")

    # Ensure engines/astro is importable for the llm package.
    import sys
    from pathlib import Path
    eng = Path(__file__).resolve().parent / "engines" / "astro"
    if eng.is_dir() and str(eng) not in sys.path:
        sys.path.insert(0, str(eng))

    question = (body.message or "").strip()
    chat_append(rid, user["id"], "user", question)
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in chat_history(rid, user["id"], limit=20)
    ]

    refusal = (
        "I can only talk about what is already in your reading. "
        "That question goes beyond the facts we have here."
    )
    try:
        pc = None
        cid = rep.get("chart_id")
        if cid:
            try:
                from core.db import chart_get
                from astro_precompute import resolve_precompute
                cinfo = chart_get(cid)
                if cinfo:
                    pc = resolve_precompute(
                        cinfo.get("person_name") or "Seeker",
                        str(cinfo.get("dob")),
                        birth_time=str(cinfo.get("tob") or "12:00"),
                        latitude=float(cinfo.get("lat") or 0.0),
                        longitude=float(cinfo.get("lon") or 0.0),
                        timezone=float(cinfo.get("tz_offset") or 5.5)
                    )
            except Exception as e_pc:
                print(f"[chat] resolve_precompute error: {e_pc}", flush=True)

        if pc and str(facts.get("kind") if isinstance(facts, dict) else "") != "palm":
            from confluence_question_engine import answer_chat_with_confluence
            lang = str(meta.get("language") or "en")
            result = answer_chat_with_confluence(
                pc, question, history=history[:-1], lang=lang)
        else:
            from llm.humanize import humanize_chat
            from llm.rules import OUT_OF_SCOPE_REFUSAL
            refusal = OUT_OF_SCOPE_REFUSAL
            result = humanize_chat(facts, question, history=history[:-1])

        answer = (result.get("answer") or refusal).strip()
        out_of_scope = bool(result.get("out_of_scope"))
        used = list(result.get("used_fact_ids") or [])
        reasons = (result.get("stats") or {}).get("rejection_reasons") or []
        if reasons:
            print(f"[chat] {rid} answer rejected by QA: {reasons}", flush=True)
    except Exception as exc:                                          # noqa: BLE001
        print(f"[chat] failed: {type(exc).__name__}: {exc}", flush=True)
        answer = refusal
        out_of_scope = True
        used = []

    chat_append(rid, user["id"], "assistant", answer,
                meta={"out_of_scope": out_of_scope, "used_fact_ids": used})
    return {
        "reportId": rid,
        "answer": answer,
        "out_of_scope": out_of_scope,
        "used_fact_ids": used,
    }


@app.get("/api/reading/{rid}/full")
def reading_full(rid: str, user: dict = Depends(current_user)):
    """Paid half after unlock.

    Palmistry used to return a JSON body here; it now stores HTML like
    astrology. JSON keys still work for any legacy report; HTML reports
    return signed links so the site can iframe the paid document.
    """
    rep = report_get(rid, user["id"])
    if not rep:
        raise HTTPException(404, "no such report")
    if not _report_unlocked(rep, user["id"]):
        raise HTTPException(402, "payment required")
    key = rep.get("paid_key") or ""
    try:
        data = store().get(key)
    except Exception:                                                 # noqa: BLE001
        raise HTTPException(404, "the stored report is missing")
    if key.endswith(".json"):
        try:
            return json.loads(data.decode())
        except Exception:                                             # noqa: BLE001
            raise HTTPException(404, "the stored report is missing")
    return {"reportId": rid, "paid": True,
            "links": _links(rid, user["id"], True)}


# ===========================================================================
# payments
# ===========================================================================
class OrderIn(BaseModel):
    item: str
    refId: Optional[str] = None
    idempotencyKey: Optional[str] = None
    turnstileToken: str = ""


class CheckoutVerifyIn(BaseModel):
    """The success payload Razorpay Checkout hands the browser, relayed back."""
    orderId: str = ""                 # our public id, for the audit trail
    razorpayOrderId: str = ""
    razorpayPaymentId: str = ""
    razorpaySignature: str = ""


@app.get("/api/prices")
def prices():
    return {"prices": {k: v // 100 for k, v in S.prices.items()},
            "currency": "INR",
            "subscriptionIncludes": {"dailyReading": True,
                                     "horaryPerMonth": S.sub_horary_per_month,
                                     "muhurat": "unlimited"}}


@app.post("/api/order")
def create_order(body: OrderIn, request: Request, user: dict = Depends(current_user)):
    TS.require_human(request, token=body.turnstileToken)
    ref_id = (body.refId or "").strip() or None
    if ref_id:
        try:
            ref_id = str(uuid.UUID(ref_id))
        except ValueError:
            raise HTTPException(400, "bad report id")
    if not ref_id and body.item not in billing.ACCOUNT_WIDE_ITEMS:
        # A per-report purchase with no report id would be granted account-wide
        # (ref_id NULL matches every report of that kind, now and in future) and
        # would never flag the report the customer actually bought. Bind it to
        # their most recent report of that kind instead.
        ref_id = billing.latest_report_id(user["id"], body.item)
    elif ref_id:
        # The report being bought must be the caller's own.
        from sqlalchemy import text as _t
        with engine().connect() as c:
            owner = c.execute(_t("SELECT user_id FROM reports WHERE id = :r"),
                              {"r": ref_id}).fetchone()
        if owner is not None and str(owner[0]) != str(user["id"]):
            raise HTTPException(403, "that report is not yours")
    try:
        if billing.already_unlocked(user["id"], body.item, ref_id):
            # Never charge twice for something already unlocked.
            return {"status": "paid", "item": body.item, "amount": 0,
                    "alreadyUnlocked": True}
    except Exception:                                                # noqa: BLE001
        pass
    try:
        out = billing.create_order(user["id"], body.item, ref_id=ref_id,
                                   idempotency_key=body.idempotencyKey)
    except KeyError:
        raise HTTPException(400, "unknown item")
    # Demo unlock: when code-level auto-pay is on and no Razorpay key exists,
    # mark paid immediately. Do not require ENV=dev — Railway staging often
    # sets ENV=prod while still testing without a gateway.
    if (S.dev_auto_pay and not S.razorpay_key_id
            and out.get("status") == "created"):
        billing.mark_paid(out["orderId"])
        out["status"] = "paid"
        out["demoPay"] = True
    return out


@app.get("/api/order/{public_id}")
def order_status(public_id: str, user: dict = Depends(current_user)):
    o = billing.order_by_public(public_id)
    if not o or o["user_id"] != user["id"]:
        raise HTTPException(404, "no such order")
    return {"orderId": o["public_id"], "status": o["status"], "item": o["item"],
            "amount": o["amount_paise"] // 100}


@app.post("/api/order/{public_id}/complete-dev")
def order_complete_dev(public_id: str, user: dict = Depends(current_user)):
    """Manual demo unlock for orders stuck at 'created' (no Razorpay)."""
    if not S.dev_auto_pay or S.razorpay_key_id:
        raise HTTPException(403, "demo unlock is off")
    o = billing.order_by_public(public_id)
    if not o or o["user_id"] != user["id"]:
        raise HTTPException(404, "no such order")
    billing.mark_paid(public_id)
    return {"orderId": public_id, "status": "paid", "demoPay": True}


@app.post("/api/order/{public_id}/mark-paid")
def order_mark_paid_admin(public_id: str, user: dict = Depends(current_user)):
    """Admin-only: confirm a payment that Razorpay captured but webhook missed."""
    if not is_admin(user):
        raise HTTPException(403, "admin only")
    o = billing.order_by_public(public_id)
    if not o:
        raise HTTPException(404, "no such order")
    result = billing.mark_paid(public_id)
    print(f"[billing] admin unlock by {user.get('email')} for order {public_id}",
          flush=True)
    return {**result, "orderId": public_id, "status": "paid",
            "item": o["item"], "refId": o.get("ref_id"),
            "amount": o["amount_paise"] // 100}


def _admin_order_report(public_id: str, user: dict) -> tuple[dict, dict]:
    """(order, report row) for an admin tool; raises a readable 4xx otherwise."""
    if not is_admin(user):
        raise HTTPException(403, "admin only")
    o = billing.order_by_public(public_id.strip().upper())
    if not o:
        raise HTTPException(404, "no such order")
    if o["item"] in billing.ACCOUNT_WIDE_ITEMS:
        raise HTTPException(400, "this order is not for a single report")
    rid = o.get("ref_id") or billing.latest_report_id(o["user_id"], o["item"])
    rep = report_get(str(rid)) if rid else None
    if not rep:
        raise HTTPException(404, "no report found for this order")
    return o, rep


@app.post("/api/admin/order/{public_id}/regenerate-report")
def admin_regenerate_report(public_id: str, force: bool = False,
                            user: dict = Depends(current_user)):
    """Admin-only: rebuild a lost report from the original request, under the
    SAME report id, so the customer's order and links keep working."""
    o, rep = _admin_order_report(public_id, user)
    rid = str(rep["id"])
    key = rep.get("paid_key") or ""
    try:
        present = bool(key) and store().exists(key)
    except Exception:                                                 # noqa: BLE001
        present = False
    if present and not force:
        return {"status": "exists", "reportId": rid,
                "message": "The report file is already on the server."}
    if not Q.r().set(f"regen:{rid}", "1", nx=True, ex=900):
        raise HTTPException(409, "A rebuild of this report is already running.")
    try:
        job = Q.enqueue(kind="admin_regenerate", user_id=str(rep["user_id"]),
                        payload={"reportId": rid}, priority=1)
        job_insert(public_id=job["jobId"], user_id=rep["user_id"],
                   kind="admin_regenerate", payload={"reportId": rid}, priority=1)
    except Exception:
        Q.r().delete(f"regen:{rid}")
        raise
    print(f"[billing] admin REGENERATE by {user.get('email')} order={o['public_id']} "
          f"report={rid} job={job['jobId']}", flush=True)
    return {"status": "queued", "jobId": job["jobId"], "reportId": rid}


@app.get("/api/admin/order/{public_id}/report")
def admin_order_report(public_id: str, format: str = "pdf",
                       user: dict = Depends(current_user)):
    """Admin-only: download the customer's full report, by order id, to send on."""
    o, rep = _admin_order_report(public_id, user)
    rid = str(rep["id"])
    if format == "html":
        key = rep.get("paid_key") or ""
        try:
            data = store().get(key) if key else None
        except Exception:                                             # noqa: BLE001
            data = None
        if not data:
            raise HTTPException(404, "the stored report is missing — regenerate it first")
        name = _pdf_name(rep).rsplit(".", 1)[0] + ".html"
        return Response(content=data, media_type="text/html; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{name}"',
                                 "Cache-Control": "private, no-store"})
    return report_pdf(rid, True, user)


@app.post("/api/order/{public_id}/revoke-access")
def order_revoke_access_admin(public_id: str, user: dict = Depends(current_user)):
    """Admin-only: take back what a paid order unlocked (the payment record stays)."""
    if not is_admin(user):
        raise HTTPException(403, "admin only")
    o = billing.order_by_public(public_id.strip().upper())
    if not o:
        raise HTTPException(404, "no such order")
    n = billing.revoke_order_access(o)
    print(f"[billing] admin REVOKE by {user.get('email')} for order {public_id}: "
          f"{n} entitlement(s)", flush=True)
    return {"ok": True, "orderId": o["public_id"], "revoked": n}


def _order_report_diag(c, m) -> dict:
    """Does the report behind a paid order actually exist? Row, flag,
    entitlement and the stored HTML objects, so support can see at a glance
    whether a customer's 'it is missing' is a DB problem or a lost file."""
    from sqlalchemy import text as _t
    out = {"refId": str(m.get("ref_id") or ""), "row": False, "paidFlag": False,
           "entitled": False, "freeFile": False, "paidFile": False,
           "kind": "", "created": "", "note": ""}
    try:
        ent = c.execute(_t(
            "SELECT 1 FROM entitlements WHERE user_id = :u AND item = :it "
            "AND (ref_id = :r OR ref_id IS NULL) AND revoked_at IS NULL LIMIT 1"),
            {"u": m["user_id"], "it": m["item"], "r": m.get("ref_id")}).fetchone()
        out["entitled"] = bool(ent)
        rid, fallback = m.get("ref_id"), False
        if not rid and m["item"] in ("subscription", "bundle_all"):
            out["note"] = "account-wide item, no single report"
            return out
        if not rid:
            # Orders placed without a report id: show the customer's latest
            # report of that kind, which is the one they were most likely buying.
            kind = {"palm_full": "palm", "numerology_full": "numerology"}.get(
                m["item"], m["item"])
            lr = c.execute(_t("SELECT id FROM reports WHERE user_id = :u AND kind = :k"
                              " ORDER BY created_at DESC LIMIT 1"),
                           {"u": m["user_id"], "k": kind}).fetchone()
            if not lr:
                out["note"] = "order has no report id and the customer has no report of this kind"
                return out
            rid, fallback = str(lr[0]), True
            out["refId"] = rid
        r = c.execute(_t("SELECT kind, paid, free_key, paid_key, created_at "
                         "FROM reports WHERE id = :r"), {"r": rid}).fetchone()
        if not r:
            out["note"] = "no reports row for this order's report id"
            return out
        rm = r._mapping
        out.update(row=True, paidFlag=bool(rm["paid"]), kind=rm["kind"] or "",
                   created=str(rm["created_at"] or ""))
        st = store()
        out["freeFile"] = bool(rm["free_key"]) and st.exists(rm["free_key"])
        out["paidFile"] = bool(rm["paid_key"]) and st.exists(rm["paid_key"])
        if not out["paidFile"]:
            out["note"] = "report row exists but the stored HTML file is missing"
        if fallback:
            out["note"] = ("order had no report id; showing the customer's latest "
                           + (rm["kind"] or "") + " report. " + out["note"]).strip()
    except Exception as e:  # diagnostics must never break the lookup
        out["note"] = f"check failed: {type(e).__name__}"
    return out


@app.get("/api/admin/orders-lookup")
def orders_lookup_admin(q: str = "", email: str = "", user: dict = Depends(current_user)):
    """Admin-only: look up orders by order ID (e.g. OD-77D2CC9B) or customer email address."""
    if not is_admin(user):
        raise HTTPException(403, "admin only")
    query = (q or email or "").strip()
    if not query:
        raise HTTPException(400, "order id or email is required")
    from sqlalchemy import text as _t
    with engine().connect() as c:
        if query.upper().startswith("OD-"):
            rows = c.execute(_t(
                "SELECT o.*, u.email, u.name as user_name FROM orders o "
                "JOIN users u ON o.user_id = u.id "
                "WHERE UPPER(o.public_id) = :p "
                "ORDER BY o.created_at DESC"
            ), {"p": query.upper()}).fetchall()
        else:
            rows = c.execute(_t(
                "SELECT o.*, u.email, u.name as user_name FROM orders o "
                "JOIN users u ON o.user_id = u.id "
                "WHERE LOWER(u.email) LIKE :em OR UPPER(o.public_id) = :p "
                "ORDER BY o.created_at DESC LIMIT 50"
            ), {"em": f"%{query.lower()}%", "p": query.upper()}).fetchall()

        orders = []
        for r in rows:
            m = r._mapping
            orders.append({
                "orderId": m["public_id"],
                "status": m["status"],
                "item": m["item"],
                "amount": m["amount_paise"] // 100,
                "refId": m.get("ref_id"),
                "email": m.get("email") or "",
                "userName": m.get("user_name") or "",
                "createdAt": str(m.get("created_at") or ""),
                "paidAt": str(m.get("paid_at") or ""),
                "gatewayOrderId": m.get("gateway_order_id") or "",
                "gatewayPaymentId": m.get("gateway_payment_id") or "",
                "report": _order_report_diag(c, m),
            })

        matched_users = []
        if not orders and ("@" in query or not query.upper().startswith("OD-")):
            user_rows = c.execute(_t(
                "SELECT id, email, name, created_at FROM users "
                "WHERE LOWER(email) LIKE :em LIMIT 10"
            ), {"em": f"%{query.lower()}%"}).fetchall()
            for ur in user_rows:
                um = ur._mapping
                matched_users.append({
                    "id": um["id"],
                    "email": um.get("email") or "",
                    "name": um.get("name") or "",
                    "createdAt": str(um.get("created_at") or "")
                })

    return {"query": query, "orders": orders, "matchedUsers": matched_users}


@app.get("/api/admin/order/{public_id}")
def order_lookup_admin(public_id: str, user: dict = Depends(current_user)):
    """Admin-only: who an order belongs to, so support can confirm before unlocking."""
    if not is_admin(user):
        raise HTTPException(403, "admin only")
    o = billing.order_by_public(public_id.strip().upper())
    if not o:
        raise HTTPException(404, "no such order")
    from sqlalchemy import text as _t
    email = ""
    with engine().connect() as c:
        row = c.execute(_t("SELECT email FROM users WHERE id = :u"),
                        {"u": o["user_id"]}).fetchone()
        if row:
            email = row[0] or ""
    return {"orderId": o["public_id"], "status": o["status"], "item": o["item"],
            "amount": o["amount_paise"] // 100, "refId": o.get("ref_id"),
            "email": email, "createdAt": str(o.get("created_at") or ""),
            "paidAt": str(o.get("paid_at") or ""),
            "gatewayOrderId": o.get("gateway_order_id") or "",
            "gatewayPaymentId": o.get("gateway_payment_id") or ""}


@app.get("/api/admin/payment-health")
def payment_health(user: dict = Depends(current_user)):
    """Admin-only: is the payment path actually working, and if not, where.

    Every webhook is already written to `payment_events` with its signature
    result, so whether Razorpay is reaching us — and whether our secret matches
    theirs — is a recorded fact rather than something to infer from a stuck
    modal. This reports it alongside the gateway configuration and any orders
    left unpaid.
    """
    if not is_admin(user):
        raise HTTPException(403, "admin only")
    from sqlalchemy import text as _t

    out: dict[str, Any] = {"config": {
        "gateway": S.gateway,
        "keyId": bool(S.razorpay_key_id),
        "keySecret": bool(S.razorpay_key_secret),
        "webhookSecret": bool(S.razorpay_webhook_secret),
        "paymentButtonId": bool(S.razorpay_payment_button_id),
        "env": S.env,
    }}
    with engine().connect() as c:
        rows = c.execute(_t(
            "SELECT event_type, signature_ok, order_id, received_at"
            " FROM payment_events ORDER BY received_at DESC LIMIT 10")).fetchall()
        out["recentEvents"] = [
            {"event": r[0], "signatureOk": bool(r[1]),
             "matchedOrder": bool(r[2]), "at": str(r[3])} for r in rows]
        tot = c.execute(_t("SELECT count(*) FROM payment_events")).fetchone()
        bad = c.execute(_t("SELECT count(*) FROM payment_events"
                           " WHERE signature_ok = :f"), {"f": False}).fetchone()
        unmatched = c.execute(_t("SELECT count(*) FROM payment_events"
                                 " WHERE order_id IS NULL")).fetchone()
        out["events"] = {"total": int(tot[0] or 0),
                         "badSignature": int(bad[0] or 0),
                         "unmatched": int(unmatched[0] or 0)}
        orows = c.execute(_t(
            "SELECT public_id, status, gateway_order_id, created_at"
            " FROM orders ORDER BY created_at DESC LIMIT 10")).fetchall()
        out["recentOrders"] = [
            {"orderId": r[0], "status": r[1],
             "hasGatewayOrder": bool(r[2]), "at": str(r[3])} for r in orows]
        stuck = c.execute(_t(
            "SELECT count(*) FROM orders WHERE status = 'created'")).fetchone()
        out["ordersAwaitingPayment"] = int(stuck[0] or 0)
    return out


@app.post("/api/payment/verify")
def payment_verify(body: CheckoutVerifyIn, user: dict = Depends(current_user)):
    """Grant access from Razorpay's signed checkout callback.

    The webhook remains the backstop, but it is an asynchronous call that can be
    delayed or misconfigured, and while it was the only route to "paid" a
    successful charge could leave the report locked indefinitely. This path
    carries the same HMAC proof, so it is trusted on the same terms: the
    signature is checked against our key secret, and the gateway order must
    resolve to an order this very user owns.
    """
    if not billing.verify_checkout_signature(
            gateway_order_id=body.razorpayOrderId,
            payment_id=body.razorpayPaymentId,
            signature=body.razorpaySignature):
        billing.record_event(None, "checkout.verify.bad_signature",
                             {"orderId": body.orderId,
                              "razorpayOrderId": body.razorpayOrderId}, False)
        raise HTTPException(400, "signature verification failed")

    o = billing.order_by_gateway_order_id(body.razorpayOrderId)
    if not o and body.orderId:
        o = billing.order_by_public(body.orderId)
    if not o:
        raise HTTPException(404, "no such order")
    if o["user_id"] != user["id"]:
        raise HTTPException(403, "not your order")

    billing.record_event(o["id"], "checkout.verify", body.model_dump(), True)
    result = billing.mark_paid(o["public_id"],
                               gateway_payment_id=body.razorpayPaymentId)
    return {**result, "orderId": o["public_id"], "status": "paid"}


@app.get("/api/place")
def place_lookup(q: str = "", limit: int = 8):
    """City name -> coordinates and UTC offset. Public, and no network call.

    Asking a customer for their latitude is asking them to do our job. Worse, it
    invites a silent wrong answer: a mistyped longitude still produces a
    confident, completely different chart, and nothing downstream can tell.

    This resolves against the world-cities table PyJHora already ships, so it
    needs no Google key, no rate limit and no internet — which also means it
    cannot become a runtime dependency that takes the form down.
    """
    q = (q or "").strip()
    if len(q) < 2:
        return {"query": q, "results": []}
    try:
        from birth_place_resolve import search_places
        rows = search_places(q, limit=max(1, min(int(limit), 20)))
    except Exception as exc:                                         # noqa: BLE001
        # The form must stay usable by hand if the table is unavailable.
        print(f"[api] place lookup unavailable: {type(exc).__name__}: {exc}",
              flush=True)
        return {"query": q, "results": [], "unavailable": True}
    return {"query": q, "results": rows}


class PromoIn(BaseModel):
    code: str


@app.get("/api/promo/{code}")
def promo_status(code: str):
    """Public, unauthenticated — the landing page shows how many places are
    left. Deliberately exposes only counts, never who redeemed."""
    return promo.status(code)


@app.post("/api/promo/redeem")
def promo_redeem(body: PromoIn, user: dict = Depends(current_user)):
    """One slot, one account. Every refusal is a 400 with a sentence a person
    can read — an exhausted code is a normal outcome, not a server error."""
    from core.errors import UserError
    try:
        result = promo.redeem(user["id"], body.code)
    except UserError as e:
        raise HTTPException(400, str(e))
    return {**result, **_me(user)}


@app.post("/api/payment/webhook")
async def payment_webhook(request: Request):
    """
    The ONLY route that grants access. Requires a valid gateway signature —
    an unsigned call is recorded and rejected, never honoured.
    """
    raw = await request.body()
    sig = (request.headers.get("x-razorpay-signature")
           or request.headers.get("x-webhook-signature") or "")
    ok = billing.verify_razorpay_signature(raw, sig)
    try:
        payload = json.loads(raw or b"{}")
    except ValueError:
        payload = {}

    public_id = (payload.get("orderId")
                 or _dig(payload, "payload", "payment", "entity", "notes", "receipt")
                 or _dig(payload, "payload", "order", "entity", "receipt"))
    order = billing.order_by_public(public_id) if public_id else None
    billing.record_event(order["id"] if order else None,
                         payload.get("event", "unknown"), payload, ok)

    if not ok:
        # In dev, allow an explicitly flagged local override so the flow can be
        # exercised without a gateway. Never in production.
        if S.env == "prod" or not S.dev_login:
            raise HTTPException(401, "signature verification failed")

    event = payload.get("event", "")
    pay_entity = _dig(payload, "payload", "payment", "entity") or {}
    if not order:
        notes = pay_entity.get("notes") if isinstance(pay_entity, dict) else {}
        if not isinstance(notes, dict):
            notes = {}
        email = (pay_entity.get("email")
                 or (pay_entity.get("contact") if "@" in str(pay_entity.get("contact") or "") else "")
                 or "")
        amount = pay_entity.get("amount") or 0
        pay_id = pay_entity.get("id") or ""
        receipt = (notes.get("receipt") or notes.get("orderId") or notes.get("order_id")
                   or public_id or "")
        # Only settled money unlocks a report. `payment.authorized` means the
        # bank has reserved the funds and nothing more — it can still fail or be
        # voided — and an event with no name at all was matching this list too,
        # which let any signed payload with an amount grant access by guesswork.
        if amount and event in ("payment.captured", "order.paid"):
            matched = billing.mark_paid_from_gateway_payment(
                email=str(email), amount_paise=int(amount),
                gateway_payment_id=str(pay_id), receipt=str(receipt or ""))
            if matched:
                return matched
        raise HTTPException(404, "order not found")

    if event.startswith("refund") or payload.get("refund"):
        billing.refund(order["public_id"])
        return {"ok": True, "refunded": True}

    if event and event not in ("payment.captured", "order.paid"):
        return {"ok": True, "ignored": event}

    pay_id = _dig(payload, "payload", "payment", "entity", "id") or ""
    paid_amount = int(pay_entity.get("amount") or 0) if isinstance(pay_entity, dict) else 0
    if paid_amount and paid_amount < order["amount_paise"]:
        # A signed payment for less than the order is not a full purchase.
        billing.record_event(order["id"], "payment.underpaid",
                             {"paid": paid_amount, "expected": order["amount_paise"]}, ok)
        return {"ok": False, "underpaid": True}
    return billing.mark_paid(order["public_id"], gateway_payment_id=pay_id)


def _dig(d: Any, *path: str):
    cur = d
    for k in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


# ===========================================================================
# misc
# ===========================================================================
class Enquiry(BaseModel):
    name: str
    phone: str
    email: str
    message: str
    turnstileToken: str = ""
    # Honeypot — real users leave blank; bots often fill it.
    website: str = ""


@app.post("/api/enquiry")
def enquiry(body: Enquiry, request: Request):
    if (body.website or "").strip():
        return {"ok": True}  # silently accept spam
    TS.require_human(request, token=body.turnstileToken)
    from core.mail import notify_new_enquiry
    from sqlalchemy import text as _t
    eid = new_id()
    ts = now()
    with tx() as c:
        c.execute(_t("INSERT INTO enquiries (id,user_id,name,phone,email,message,"
                     "status,created_at) VALUES (:i,:u,:n,:p,:e,:m,'new',:t)"),
                  {"i": eid, "u": None, "n": body.name.strip(),
                   "p": body.phone.strip(), "e": body.email.strip(),
                   "m": body.message.strip(), "t": ts})
    notify_new_enquiry(enquiry_id=eid, name=body.name.strip(),
                       phone=body.phone.strip(), email=body.email.strip(),
                       message=body.message.strip(), created_at=ts)
    return {"ok": True}


class Notify(BaseModel):
    email: str
    topic: str = "launch"
    turnstileToken: str = ""
    website: str = ""


@app.post("/api/notify")
def notify(body: Notify, request: Request):
    if (body.website or "").strip():
        return {"ok": True}
    TS.require_human(request, token=body.turnstileToken)
    from sqlalchemy import text as _t
    with tx() as c:
        c.execute(_t("INSERT INTO waitlist (email,topic,created_at) VALUES (:e,:tp,:t)"
                     + (" ON CONFLICT (email) DO NOTHING" if S.is_postgres
                        else " ON CONFLICT DO NOTHING")),
                  {"e": body.email, "tp": body.topic, "t": now()})
    return {"ok": True}


def _semantic_health() -> dict:
    """Report whether MiniLM is active or the lexical fallback is in use."""
    import sys
    from pathlib import Path

    astro = Path(__file__).resolve().parent / "engines" / "astro"
    for p in (str(astro), str(astro.parent), str(astro.parent.parent)):
        if p not in sys.path:
            sys.path.insert(0, p)
    try:
        import semantic_fallback
        from local_models import model_status

        degraded = semantic_fallback.degraded()
        return {"mode": "degraded_lexical" if degraded else "minilm",
                "models": model_status(),
                "with_confluence": os.getenv("WITH_CONFLUENCE", "1")}
    except Exception as exc:                                        # noqa: BLE001
        return {"mode": "unknown", "error": f"{type(exc).__name__}: {exc}"}


@app.get("/health")
def health():
    db_ok = True
    try:
        with engine().connect() as c:
            c.exec_driver_sql("SELECT 1")
    except Exception:                                                 # noqa: BLE001
        db_ok = False
    q = Q.health()
    queue_ok = q.get("mode") != "unavailable"
    return {"ok": db_ok and queue_ok, "env": S.env, "db": db_ok, "queue": q,
            "semantic": _semantic_health()}


@app.get("/api/queue")
def queue_stats():
    return Q.health()
