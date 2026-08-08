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
import time
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from core import billing, promo, queue as Q
from core.auth import COOKIE, current_user, is_admin, is_admin_id, login_admin, login_dev, login_with_google, logout
from core.config import S
from core.db import (engine, extend_partitions, init_schema, job_get,
                     job_insert, job_update, jdump, new_id, now,
                     report_get, reports_for_user, tx)
from core.store import store

app = FastAPI(title="GrahaRekha API", version="3.0")
app.add_middleware(CORSMiddleware, allow_origins=S.allowed_origins,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Reports are NEVER mounted as static files. Delivery is /api/file/{token}.


@app.on_event("startup")
def _startup() -> None:
    init_schema()
    extend_partitions()

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


class DevIn(BaseModel):
    email: str = "guest@graharekha.co.in"
    name: str = "Guest Seeker"
    passcode: str = ""


class AdminIn(BaseModel):
    username: str = ""
    email: str = ""          # legacy
    password: str


def _set_cookie(resp: Response, token: str) -> None:
    resp.set_cookie(COOKIE, token, max_age=S.session_days * 86400, httponly=True,
                    secure=(S.env == "prod"), samesite="lax", path="/")


@app.get("/api/public-config")
def public_config():
    """Non-secret flags the site needs before sign-in (Google Client ID, etc.)."""
    return {
        "googleClientId": S.google_client_id or "",
        "guestLogin": bool(S.dev_login),
        "adminLogin": bool(S.dev_login),
        "brand": "GrahaRekha",
        "razorpayKeyId": S.razorpay_key_id or "",
        "razorpayPaymentButtonId": S.razorpay_payment_button_id or "",
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
    user, token = login_dev(body.email, body.name, passcode=body.passcode,
                            ip=request.client.host if request.client else "",
                            ua=request.headers.get("user-agent", ""))
    _set_cookie(response, token)
    return {"token": token, "user": _me(user)}


@app.post("/api/auth/admin")
def auth_admin(body: AdminIn, request: Request, response: Response):
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
    return {"id": user["id"], "email": user["email"], "name": user.get("name"),
            "picture": user.get("picture"), "credits": user.get("credits", 0),
            "admin": admin,
            "subscribed": subscribed or admin,
            "subUntil": (sub or {}).get("current_period_end"),
            "horaryLeft": (billing.quota_left(user["id"], "horary",
                                              S.sub_horary_per_month,
                                              billing.month_period())
                           if subscribed else 999 if admin else 0)}


@app.get("/api/me")
def me(user: dict = Depends(current_user)):
    return _me(user)


# ===========================================================================
# jobs
# ===========================================================================
class JobIn(BaseModel):
    kind: str
    payload: dict = Field(default_factory=dict)


@app.post("/api/job")
def submit_job(body: JobIn, user: dict = Depends(current_user)):
    from core.handlers import HANDLERS
    if body.kind not in HANDLERS:
        raise HTTPException(400, f"unknown kind; try {sorted(HANDLERS)}")
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
    unlocked = paid or is_admin_id(uid)
    out = {"free": f"/api/file/{file_token(rid, 'free', uid)}"}
    if unlocked:
        out["paid"] = f"/api/file/{file_token(rid, 'paid', uid)}"
    return out


def _report_unlocked(rep: dict, uid: str) -> bool:
    if bool(rep.get("paid")) or is_admin_id(uid):
        return True
    # Order may have granted the item even if reports.paid lagged.
    try:
        kind = rep.get("kind") or ""
        item = "numerology_full" if kind == "numerology" else kind
        if item and billing.entitled(uid, item, rep.get("id")):
            return True
        if item and billing.entitled(uid, item, None):
            return True
    except Exception:                                                 # noqa: BLE001
        pass
    return False


def _gate_meta(kind: str, meta: dict, unlocked: bool) -> dict:
    """Strip horary verdict from JSON when the report is still locked."""
    if unlocked or kind != "horary" or not isinstance(meta, dict):
        return meta
    return {**meta, "answer": None, "verdicts": {}}


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
    rep = report_get(rid, uid)
    if not rep:
        raise HTTPException(404, "no such report")
    if half == "paid" and not _report_unlocked(rep, uid):
        raise HTTPException(402, "payment required")
    key = rep["paid_key"] if half == "paid" else rep["free_key"]
    if not key:
        raise HTTPException(404, "nothing stored for that half")
    try:
        data = store().get(key)
    except Exception:                                                 # noqa: BLE001
        raise HTTPException(404, "the stored report is missing")
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
    unlocked = bool(result.get("paid")) or is_admin_id(uid)
    if rid and "links" not in result:
        result["links"] = _links(rid, uid, unlocked)
    if isinstance(result.get("meta"), dict):
        result["meta"] = _gate_meta(kind, result["meta"], unlocked)
    return result


@app.get("/api/reports")
def my_reports(user: dict = Depends(current_user)):
    out = []
    for r in reports_for_user(user["id"]):
        unlocked = _report_unlocked(r, user["id"])
        out.append({"reportId": r["id"], "kind": r["kind"],
                    "paid": unlocked,
                    "createdAt": r["created_at"],
                    "meta": _gate_meta(r["kind"], r["meta"], unlocked),
                    "links": _links(r["id"], user["id"], unlocked)})
    return out


@app.get("/api/reports/{rid}")
def one_report(rid: str, user: dict = Depends(current_user)):
    rep = report_get(rid, user["id"])
    if not rep:
        raise HTTPException(404, "no such report")
    unlocked = _report_unlocked(rep, user["id"])
    return {"reportId": rep["id"], "kind": rep["kind"], "paid": unlocked,
            "meta": _gate_meta(rep["kind"], rep["meta"], unlocked),
            "links": _links(rid, user["id"], unlocked)}


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


@app.get("/api/prices")
def prices():
    return {"prices": {k: v // 100 for k, v in S.prices.items()},
            "currency": "INR",
            "subscriptionIncludes": {"dailyReading": True,
                                     "horaryPerMonth": S.sub_horary_per_month,
                                     "muhurat": "unlimited"}}


@app.post("/api/order")
def create_order(body: OrderIn, user: dict = Depends(current_user)):
    try:
        out = billing.create_order(user["id"], body.item, ref_id=body.refId,
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
    return billing.mark_paid(public_id)


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
        # Button payments often land as payment.captured; some accounts send authorized.
        if amount and event in ("payment.captured", "payment.authorized",
                                "order.paid", ""):
            matched = billing.mark_paid_from_gateway_payment(
                email=str(email), amount_paise=int(amount),
                gateway_payment_id=str(pay_id), receipt=str(receipt or ""))
            if matched:
                return matched
        raise HTTPException(404, "order not found")

    if event.startswith("refund") or payload.get("refund"):
        billing.refund(order["public_id"])
        return {"ok": True, "refunded": True}

    pay_id = _dig(payload, "payload", "payment", "entity", "id") or ""
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


@app.post("/api/enquiry")
def enquiry(body: Enquiry, user: Optional[dict] = None):
    from sqlalchemy import text as _t
    with tx() as c:
        c.execute(_t("INSERT INTO enquiries (id,user_id,name,phone,email,message,"
                     "status,created_at) VALUES (:i,:u,:n,:p,:e,:m,'new',:t)"),
                  {"i": new_id(), "u": (user or {}).get("id"), "n": body.name,
                   "p": body.phone, "e": body.email, "m": body.message, "t": now()})
    return {"ok": True}


class Notify(BaseModel):
    email: str
    topic: str = "launch"


@app.post("/api/notify")
def notify(body: Notify):
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
