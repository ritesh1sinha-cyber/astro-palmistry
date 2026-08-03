#!/usr/bin/env python3
"""
astro_server.py — product/web layer for the Vedic astrology engine.
===================================================================

Adds ONLY what a paid product needs. The engine (astro_report_generator.py and
the 200+ lane modules) is imported, never modified.

  * real user accounts (SQLite) via Google Sign-In  — the engine had one shared password
  * credit wallet + orders + UPI payment gating
  * 3-slot job queue with queue position and self-correcting ETA
  * free/paid split of confluence + user report (astro_split.py)
  * SIGNED, OWNERSHIP-CHECKED report delivery  — closes the /reports/* leak
  * daily reading subscription, horary, numerology, matching, muhurat, timing

Run:
    uvicorn astro_server:app --host 0.0.0.0 --port 8100

Frontend: set CONFIG.astroApiBase in index.html to this server's URL.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
import uuid
from collections import deque
from contextlib import closing
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

HERE = Path(__file__).resolve().parent
REPORTS = HERE / "reports"
DB_PATH = Path(os.getenv("ASTRO_DB", HERE / "astro.db"))
SECRET = os.getenv("ASTRO_SECRET", "change-me-in-production")

# ---------------------------------------------------------------------------
# Pricing (paise-free rupees; mirror in the frontend CONFIG)
# ---------------------------------------------------------------------------
PRICES = {
    "full_report":   1499,
    "horary":          99,
    "future_event":   199,
    "kundali_match":  299,
    "muhurat":         49,
    "btr":            999,
    "subscription":   199,      # per month — includes daily + 3 horary
}
SUB_HORARY_ALLOWANCE = 3
MAX_CONCURRENT = int(os.getenv("ASTRO_MAX_CONCURRENT", "3"))
REPORT_AVG_SECONDS = float(os.getenv("ASTRO_AVG_SECONDS", "150"))
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
UPI_ID = os.getenv("UPI_ID", "astropalmistry@upi")
PAYEE = os.getenv("PAYEE_NAME", "Astro Palmistry")

app = FastAPI(title="Astro Palmistry — astrology API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# NOTE: we deliberately do NOT mount /reports as static files. That public mount
# is exactly how the original app leaked paid reports. Delivery goes through
# /api/astro/file/{token} below, which checks ownership and payment.


# ===========================================================================
# 1. Storage
# ===========================================================================
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY, email TEXT UNIQUE, name TEXT, picture TEXT,
  credits INTEGER DEFAULT 0, sub_until TEXT, sub_horary_used INTEGER DEFAULT 0,
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS charts (
  id TEXT PRIMARY KEY, user_id TEXT, name TEXT, dob TEXT, tob TEXT,
  place TEXT, lat REAL, lon REAL, tz REAL, gender INTEGER,
  slug TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS reports (
  id TEXT PRIMARY KEY, user_id TEXT, chart_id TEXT, kind TEXT,
  paid INTEGER DEFAULT 0, free_path TEXT, paid_path TEXT, meta TEXT,
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS orders (
  id TEXT PRIMARY KEY, user_id TEXT, item TEXT, ref_id TEXT,
  amount INTEGER, status TEXT DEFAULT 'pending', created_at TEXT, paid_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_reports_user ON reports(user_id);
CREATE INDEX IF NOT EXISTS ix_orders_user ON orders(user_id);
"""


def db():
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    return con


def init_db():
    with closing(db()) as con:
        con.executescript(SCHEMA)
        con.commit()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ===========================================================================
# 2. Auth — real per-user accounts via Google Sign-In
# ===========================================================================
def _sign(payload: str) -> str:
    return hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]


def make_session_token(user_id: str) -> str:
    exp = int(time.time()) + 60 * 60 * 24 * 30
    body = f"{user_id}.{exp}"
    return f"{body}.{_sign(body)}"


def read_session_token(tok: str) -> Optional[str]:
    try:
        uid, exp, sig = tok.rsplit(".", 2)
    except ValueError:
        return None
    if not hmac.compare_digest(sig, _sign(f"{uid}.{exp}")):
        return None
    if int(exp) < time.time():
        return None
    return uid


def verify_google_id_token(token: str) -> dict:
    """
    Verify a Google ID token. Uses google-auth when available; otherwise refuses
    rather than trusting an unverified JWT (the previous code trusted the client).
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(503, "GOOGLE_CLIENT_ID is not configured")
    try:
        from google.auth.transport import requests as g_requests
        from google.oauth2 import id_token as g_id_token
    except ImportError as exc:                                   # pragma: no cover
        raise HTTPException(503, "pip install google-auth to enable Google sign-in") from exc
    info = g_id_token.verify_oauth2_token(token, g_requests.Request(), GOOGLE_CLIENT_ID)
    if info.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise HTTPException(401, "bad issuer")
    return info


class LoginIn(BaseModel):
    idToken: str


@app.post("/api/astro/login")
async def login(body: LoginIn):
    info = verify_google_id_token(body.idToken)
    uid = "u_" + hashlib.sha256(info["sub"].encode()).hexdigest()[:16]
    with closing(db()) as con:
        row = con.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        if row is None:
            con.execute(
                "INSERT INTO users (id,email,name,picture,credits,created_at) VALUES (?,?,?,?,?,?)",
                (uid, info.get("email"), info.get("name"), info.get("picture"), 0, now_iso()),
            )
            con.commit()
    return {"token": make_session_token(uid), "user": _user_public(uid)}


class DevLoginIn(BaseModel):
    email: str = "dev@example.com"
    name: str = "Dev User"


@app.post("/api/astro/dev-login")
async def dev_login(body: DevLoginIn):
    """
    Local development only — set ASTRO_DEV_LOGIN=1 to enable. Never enable in
    production: it mints a session for any email with no verification.
    """
    if os.getenv("ASTRO_DEV_LOGIN") != "1":
        raise HTTPException(404, "not enabled")
    uid = "u_dev_" + hashlib.sha256(body.email.encode()).hexdigest()[:12]
    with closing(db()) as con:
        if con.execute("SELECT 1 FROM users WHERE id=?", (uid,)).fetchone() is None:
            con.execute("INSERT INTO users (id,email,name,picture,credits,created_at)"
                        " VALUES (?,?,?,?,0,?)",
                        (uid, body.email, body.name, "", now_iso()))
            con.commit()
    return {"token": make_session_token(uid), "user": _user_public(uid)}


def _user_public(uid: str) -> dict:
    with closing(db()) as con:
        r = con.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if not r:
        raise HTTPException(404, "no such user")
    sub_active = bool(r["sub_until"] and r["sub_until"] > now_iso())
    return {
        "id": r["id"], "email": r["email"], "name": r["name"], "picture": r["picture"],
        "credits": r["credits"], "subscribed": sub_active, "subUntil": r["sub_until"],
        "horaryLeft": max(0, SUB_HORARY_ALLOWANCE - (r["sub_horary_used"] or 0)) if sub_active else 0,
    }


async def current_user(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    tok = auth[7:] if auth.lower().startswith("bearer ") else request.cookies.get("astro_session", "")
    uid = read_session_token(tok) if tok else None
    if not uid:
        raise HTTPException(401, "sign in required")
    return uid


@app.get("/api/astro/me")
async def me(uid: str = Depends(current_user)):
    return _user_public(uid)


# ===========================================================================
# 3. Payments — credits wallet + UPI orders
# ===========================================================================
class OrderIn(BaseModel):
    item: str
    refId: Optional[str] = None


@app.post("/api/astro/order")
async def create_order(body: OrderIn, uid: str = Depends(current_user)):
    if body.item not in PRICES:
        raise HTTPException(400, "unknown item")
    amount = PRICES[body.item]
    oid = "OD-" + uuid.uuid4().hex[:8].upper()
    with closing(db()) as con:
        con.execute("INSERT INTO orders (id,user_id,item,ref_id,amount,status,created_at)"
                    " VALUES (?,?,?,?,?,'pending',?)",
                    (oid, uid, body.item, body.refId, amount, now_iso()))
        con.commit()
    intent = (f"upi://pay?pa={UPI_ID}&pn={PAYEE.replace(' ', '%20')}"
              f"&am={amount}&cu=INR&tr={oid}&tn={body.item}")
    return {"orderId": oid, "amount": amount, "item": body.item,
            "upiIntentUrl": intent, "qrImage": None}


@app.get("/api/astro/order/{oid}")
async def order_status(oid: str, uid: str = Depends(current_user)):
    with closing(db()) as con:
        r = con.execute("SELECT * FROM orders WHERE id=? AND user_id=?", (oid, uid)).fetchone()
    if not r:
        raise HTTPException(404, "no such order")
    return {"orderId": r["id"], "status": r["status"], "item": r["item"], "amount": r["amount"]}


@app.post("/api/astro/payment/webhook")
async def payment_webhook(payload: Dict[str, Any]):
    """
    Your PSP calls this. VERIFY THE SIGNATURE HERE before trusting it — this is
    the only place an order may be marked paid.
    """
    oid = payload.get("orderId")
    with closing(db()) as con:
        r = con.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
        if not r:
            raise HTTPException(404, "no such order")
        if r["status"] == "paid":
            return {"ok": True, "already": True}
        con.execute("UPDATE orders SET status='paid', paid_at=? WHERE id=?", (now_iso(), oid))
        item, uid, ref = r["item"], r["user_id"], r["ref_id"]

        if item == "subscription":
            u = con.execute("SELECT sub_until FROM users WHERE id=?", (uid,)).fetchone()
            base = datetime.now(timezone.utc)
            if u and u["sub_until"] and u["sub_until"] > now_iso():
                base = datetime.fromisoformat(u["sub_until"])
            con.execute("UPDATE users SET sub_until=?, sub_horary_used=0 WHERE id=?",
                        ((base + timedelta(days=30)).isoformat(), uid))
        elif item == "full_report" and ref:
            con.execute("UPDATE reports SET paid=1 WHERE id=? AND user_id=?", (ref, uid))
        elif ref:
            con.execute("UPDATE reports SET paid=1 WHERE id=? AND user_id=?", (ref, uid))
        con.commit()
    return {"ok": True}


def _entitled(uid: str, item: str, ref_id: Optional[str] = None) -> bool:
    """Paid order for this item (+ref), or an active subscription that covers it."""
    with closing(db()) as con:
        u = con.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        if u and u["sub_until"] and u["sub_until"] > now_iso():
            if item in ("daily", "muhurat"):
                return True
            if item == "horary" and (u["sub_horary_used"] or 0) < SUB_HORARY_ALLOWANCE:
                return True
        q = "SELECT 1 FROM orders WHERE user_id=? AND item=? AND status='paid'"
        args: List[Any] = [uid, item]
        if ref_id:
            q += " AND ref_id=?"
            args.append(ref_id)
        return con.execute(q + " LIMIT 1", args).fetchone() is not None


def _consume_sub_horary(uid: str) -> None:
    with closing(db()) as con:
        con.execute("UPDATE users SET sub_horary_used=COALESCE(sub_horary_used,0)+1 WHERE id=?", (uid,))
        con.commit()


# ===========================================================================
# 4. Gated report delivery — closes the public /reports leak
# ===========================================================================
def file_token(report_id: str, half: str, uid: str) -> str:
    exp = int(time.time()) + 3600
    body = f"{report_id}.{half}.{uid}.{exp}"
    return f"{body}.{_sign(body)}"


@app.get("/api/astro/file/{token}", response_class=HTMLResponse)
async def serve_report(token: str):
    try:
        rid, half, uid, exp, sig = token.rsplit(".", 4)
    except ValueError:
        raise HTTPException(400, "bad token")
    if not hmac.compare_digest(sig, _sign(f"{rid}.{half}.{uid}.{exp}")):
        raise HTTPException(403, "bad signature")
    if int(exp) < time.time():
        raise HTTPException(410, "link expired")
    with closing(db()) as con:
        r = con.execute("SELECT * FROM reports WHERE id=? AND user_id=?", (rid, uid)).fetchone()
    if not r:
        raise HTTPException(404, "no such report")
    if half == "paid" and not r["paid"]:
        raise HTTPException(402, "payment required")
    path = Path(r["paid_path"] if half == "paid" else r["free_path"])
    if not path.is_file():
        raise HTTPException(404, "file missing")
    return HTMLResponse(path.read_text(encoding="utf-8", errors="ignore"))


def _links(rid: str, uid: str, paid: bool) -> dict:
    out = {"free": f"/api/astro/file/{file_token(rid, 'free', uid)}"}
    if paid:
        out["paid"] = f"/api/astro/file/{file_token(rid, 'paid', uid)}"
    return out


# ===========================================================================
# 5. Job queue — 3 concurrent, position + self-correcting ETA
# ===========================================================================
@dataclass
class Job:
    id: str
    uid: str
    kind: str
    payload: dict
    status: str = "queued"
    queued_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    result: Optional[dict] = None
    error: Optional[str] = None


class Queue:
    def __init__(self) -> None:
        self.jobs: Dict[str, Job] = {}
        self.waiting: Deque[str] = deque()
        self.free = list(range(MAX_CONCURRENT))
        self.durations: Dict[str, Deque[float]] = {}
        self.pending: asyncio.Queue = asyncio.Queue()
        self.lock = asyncio.Lock()

    @property
    def active(self) -> int:
        return MAX_CONCURRENT - len(self.free)

    def avg(self, kind: str) -> float:
        d = self.durations.get(kind)
        return sum(d) / len(d) if d else REPORT_AVG_SECONDS

    def position(self, jid: str) -> int:
        try:
            return list(self.waiting).index(jid) + 1
        except ValueError:
            return 0

    def eta(self, job: Job) -> tuple:
        a = self.avg(job.kind)
        if job.status == "processing" and job.started_at:
            return max(0.0, a - (time.time() - job.started_at)), a
        if job.status == "queued":
            pos = self.position(job.id)
            running = [max(0.0, self.avg(j.kind) - (time.time() - j.started_at))
                       for j in self.jobs.values() if j.status == "processing" and j.started_at]
            soonest = min(running) if running else 0.0
            waves = max(0, pos - 1) // MAX_CONCURRENT
            t = soonest + waves * a + a
            return t, t
        return 0.0, a

    async def submit(self, uid: str, kind: str, payload: dict) -> Job:
        job = Job(id="AJ-" + uuid.uuid4().hex[:6].upper(), uid=uid, kind=kind, payload=payload)
        async with self.lock:
            self.jobs[job.id] = job
            self.waiting.append(job.id)
        await self.pending.put(job.id)
        await asyncio.sleep(0.05)
        return job

    def snapshot(self, job: Job) -> dict:
        eta, total = self.eta(job)
        return {"jobId": job.id, "status": job.status, "kind": job.kind,
                "queuePosition": self.position(job.id), "activeJobs": self.active,
                "etaSeconds": round(eta, 1), "etaTotalSeconds": round(total, 1),
                "result": job.result, "error": job.error}

    async def cancel(self, jid: str, uid: str) -> None:
        async with self.lock:
            j = self.jobs.get(jid)
            if j and j.uid == uid and j.status == "queued":
                j.status = "cancelled"
                if jid in self.waiting:
                    self.waiting.remove(jid)

    async def worker(self, wid: int) -> None:
        while True:
            jid = await self.pending.get()
            async with self.lock:
                job = self.jobs.get(jid)
                if not job or job.status != "queued":
                    self.pending.task_done()
                    continue
                if jid in self.waiting:
                    self.waiting.remove(jid)
                slot = self.free.pop(0) if self.free else wid
                job.status, job.started_at = "processing", time.time()
            try:
                fn = HANDLERS[job.kind]
                job.result = await asyncio.to_thread(fn, job.uid, job.payload)
                job.status = "done"
                self.durations.setdefault(job.kind, deque(maxlen=20)).append(
                    time.time() - (job.started_at or time.time()))
            except HTTPException as exc:
                job.status, job.error = "failed", str(exc.detail)
            except Exception as exc:                                  # noqa: BLE001
                job.status, job.error = "failed", f"{type(exc).__name__}: {exc}"
            finally:
                job.finished_at = time.time()
                async with self.lock:
                    if slot not in self.free:
                        self.free.append(slot)
                        self.free.sort()
                self.pending.task_done()


Q = Queue()


@app.on_event("startup")
async def _startup():
    init_db()
    REPORTS.mkdir(exist_ok=True)
    for i in range(MAX_CONCURRENT):
        asyncio.create_task(Q.worker(i))
    print(f"[astro] ready — {MAX_CONCURRENT} slots, db={DB_PATH}", flush=True)


# ===========================================================================
# 6. Engine calls (run in worker threads)
# ===========================================================================
def _chart_row(uid: str, p: dict) -> sqlite3.Row:
    """Find-or-create the chart record for this birth data."""
    slug = "".join(c for c in (p.get("name") or "chart") if c.isalnum()) or "chart"
    cid = "c_" + hashlib.sha256(
        f"{uid}|{p['dob']}|{p['tob']}|{p['lat']}|{p['lon']}".encode()).hexdigest()[:16]
    with closing(db()) as con:
        row = con.execute("SELECT * FROM charts WHERE id=?", (cid,)).fetchone()
        if row is None:
            con.execute(
                "INSERT INTO charts (id,user_id,name,dob,tob,place,lat,lon,tz,gender,slug,created_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, uid, p.get("name"), p["dob"], p["tob"], p.get("place", ""),
                 p["lat"], p["lon"], p.get("tz", 5.5), int(p.get("gender", 0)),
                 f"{slug}_{cid[-6:]}", now_iso()))
            con.commit()
            row = con.execute("SELECT * FROM charts WHERE id=?", (cid,)).fetchone()
    return row


def _precompute(chart: sqlite3.Row) -> dict:
    from astro_precompute import resolve_precompute
    return resolve_precompute(
        chart["name"] or "Seeker", chart["dob"],
        birth_time=chart["tob"], latitude=chart["lat"], longitude=chart["lon"],
        timezone=chart["tz"], place_name=chart["place"] or "", gender=chart["gender"],
    )


def _save_report(uid: str, chart_id: str, kind: str, free_html: str,
                 paid_html: str, meta: dict, paid: int = 0) -> str:
    rid = "r_" + uuid.uuid4().hex[:12]
    d = REPORTS / rid
    d.mkdir(parents=True, exist_ok=True)
    (d / "free.html").write_text(free_html or "", encoding="utf-8")
    (d / "paid.html").write_text(paid_html or "", encoding="utf-8")
    with closing(db()) as con:
        con.execute("INSERT INTO reports (id,user_id,chart_id,kind,paid,free_path,paid_path,meta,created_at)"
                    " VALUES (?,?,?,?,?,?,?,?,?)",
                    (rid, uid, chart_id, kind, paid, str(d / "free.html"),
                     str(d / "paid.html"), json.dumps(meta), now_iso()))
        con.commit()
    return rid


# ---- chart summary (free) -------------------------------------------------
def h_chart_summary(uid: str, p: dict) -> dict:
    chart = _chart_row(uid, p)
    pc = _precompute(chart)
    m = pc.get("meta") or {}
    vim = (pc.get("vimshottari") or {})
    cur = vim.get("current") or {}
    if not cur:
        today = date.today().isoformat()
        for row in (vim.get("sequence") or []):
            start, end = str(row.get("start") or ""), str(row.get("end") or "")
            if start <= today <= end:
                cur = row
                break
    planets = pc.get("planets") or {}
    moon = planets.get("Moon") or {}
    return {
        "chartId": chart["id"],
        "lagna": {"sign": m.get("lagna_sign"), "degree": m.get("lagna_degree"),
                  "nakshatra": m.get("lagna_nakshatra"), "pada": m.get("lagna_pada"),
                  "lord": m.get("lagna_lord")},
        "moon": {"sign": moon.get("sign"), "nakshatra": moon.get("nakshatra")},
        "currentDasha": {"md": cur.get("md_lord") or cur.get("lord"),
                         "ad": cur.get("ad_lord"),
                         "from": cur.get("start"), "to": cur.get("end")},
        "ayanamsa": m.get("ayanamsa"), "age": m.get("age"),
        "houseLords": pc.get("house_lords"),
        "personalNote": (lambda V: V.humanise(V.chart_opening(
            V.context_from_pc(pc, name=chart["name"] or "Seeker",
                              place=chart["place"] or "", tob=chart["tob"]))))(
            __import__("astro_voice")),
    }


# ---- numerology (free lead magnet) ---------------------------------------
def h_numerology(uid: str, p: dict) -> dict:
    """numerology_report.generate_numerology_html(name, dob: date, sex, report_date)"""
    from datetime import date as _date
    from numerology_report import generate_numerology_html
    y, m, d = (int(x) for x in p["dob"].split("-"))
    sex = {0: "Male", 1: "Female"}.get(int(p.get("gender", 0)), "—")
    html, slug = generate_numerology_html(p.get("name", "Seeker"), _date(y, m, d), sex, None)
    import astro_voice as V
    html = V.personalise(html, {"name": p.get("name", "Seeker"), "dob": p["dob"]}, "numerology")
    rid = _save_report(uid, "", "numerology", html, "", {"free": True, "slug": slug}, paid=1)
    return {"reportId": rid, "links": _links(rid, uid, True), "free": True, "slug": slug}


def _as_date(v):
    from datetime import date as _d
    if isinstance(v, _d):
        return v
    y, m, d = (int(x) for x in str(v).split("-"))
    return _d(y, m, d)


def _accepts(fn, kw: str) -> bool:
    import inspect
    try:
        return kw in inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return False


def _as_html(res: Any, out_dir: Path) -> str:
    if isinstance(res, str) and res.strip().startswith("<"):
        return res
    if isinstance(res, (str, Path)) and Path(str(res)).is_file():
        return Path(str(res)).read_text(encoding="utf-8", errors="ignore")
    for f in sorted(out_dir.glob("*.html")):
        return f.read_text(encoding="utf-8", errors="ignore")
    if isinstance(res, dict):
        return "<pre>" + json.dumps(res, indent=2, default=str) + "</pre>"
    return str(res)


# ---- full report: confluence + user report, split -------------------------
def h_full_report(uid: str, p: dict) -> dict:
    import astro_split as SP
    from vedic_confluence_report import generate_confluence_reports

    chart = _chart_row(uid, p)
    slug = chart["slug"]
    rdir = REPORTS / slug
    rdir.mkdir(parents=True, exist_ok=True)

    conf_path, user_path, _focus, payload = generate_confluence_reports(
        "", str(rdir), chart["name"] or "Seeker", chart["dob"], slug,
        client_question=p.get("question", ""),
        birth_time=chart["tob"], latitude=chart["lat"], longitude=chart["lon"],
        timezone=chart["tz"], place_name=chart["place"] or "",
        gender=chart["gender"],
    )

    import astro_voice as V
    vctx = V.context_from_pc(_precompute(chart), name=chart["name"] or "Seeker",
                             place=chart["place"] or "", tob=chart["tob"])

    conf_html = Path(conf_path).read_text(encoding="utf-8", errors="ignore")
    split = SP.split_confluence(V.personalise(conf_html, vctx, "full_report"))
    user_split = {"free_html": "", "paid_html": "", "paid_sections": []}
    if user_path and Path(user_path).is_file():
        user_split = SP.split_user_report(V.personalise(
            Path(user_path).read_text(encoding="utf-8", errors="ignore"), vctx, "full_report"))

    meta = {
        "freeSections": split["free_sections"],
        "paidSections": split["paid_sections"] + user_split.get("paid_sections", []),
        "teasers": split["teasers"],
        "price": PRICES["full_report"],
        "lanes": sorted(f.name for f in rdir.glob("*.html")),
    }
    rid = _save_report(
        uid, chart["id"], "full_report",
        split["free_html"] + user_split["free_html"],
        split["paid_html"] + user_split["paid_html"],
        meta, paid=1 if _entitled(uid, "full_report", None) else 0,
    )
    with closing(db()) as con:
        paid = con.execute("SELECT paid FROM reports WHERE id=?", (rid,)).fetchone()["paid"]
    return {"reportId": rid, "chartId": chart["id"], "paid": bool(paid),
            "meta": meta, "links": _links(rid, uid, bool(paid)),
            "price": PRICES["full_report"]}


# ---- horary --------------------------------------------------------------
def h_horary(uid: str, p: dict) -> dict:
    """
    vedic_horary_report.generate_vedic_horary_html(question, q_date, q_time, location, kp_number)
    western_horary_report.generate_western_horary_html(question, q_date, q_time, location)
    Both return (html, judgement_dict).
    """
    import astro_split as SP
    htmls, verdicts = {}, {}

    try:
        vgen = None
        if os.getenv("ASTRO_HOTFIX", "1") == "1":
            # upstream _prashna_card crashes on 8-step charts — see astro_hotfix.py
            try:
                import astro_hotfix
                vgen = astro_hotfix.horary_glyph_fix().generate_vedic_horary_html
            except Exception:                                         # noqa: BLE001
                vgen = None
        if vgen is None:
            from vedic_horary_report import generate_vedic_horary_html as vgen
        vhtml, vj = vgen(p["question"], p["qDate"], p["qTime"],
                         p.get("location", "Hyderabad"), p.get("kpNumber", ""))
        htmls["vedic"] = vhtml
        verdicts["vedic"] = {"verdict": vj.get("verdict"), "confidence": vj.get("confidence"),
                             "score": vj.get("score"), "systems": vj.get("systems")}
    except Exception as exc:                                          # noqa: BLE001
        verdicts["vedic"] = {"error": f"{type(exc).__name__}: {exc}"}

    try:
        from western_horary_report import generate_western_horary_html as wgen
        whtml, wj = wgen(p["question"], p["qDate"], p["qTime"],
                         p.get("location", "Hyderabad"))
        htmls["western"] = whtml
        verdicts["western"] = {"verdict": wj.get("verdict"), "confidence": wj.get("confidence")}
    except Exception as exc:                                          # noqa: BLE001
        verdicts["western"] = {"error": f"{type(exc).__name__}: {exc}"}

    if not htmls:
        raise HTTPException(500, "both horary engines failed: " + json.dumps(verdicts))

    entitled = _entitled(uid, "horary") or _entitled(uid, "subscription")
    if entitled and _entitled(uid, "subscription"):
        _consume_sub_horary(uid)

    import astro_voice as V
    hctx = {"name": p.get("name", "Seeker"), "question": p["question"],
            "asked": f"{p['qDate']} {p['qTime']}", "place": p.get("location", "")}
    htmls = {k: V.personalise(v, hctx, "horary") for k, v in htmls.items()}
    splits = {k: SP.split_horary(v) for k, v in htmls.items()}
    free_html = "".join(sp["free_html"] for sp in splits.values())
    paid_html = "".join(sp["paid_html"] for sp in splits.values())
    paid_sections, teasers = [], {}
    for tag, sp in splits.items():
        paid_sections += [f"{tag.title()}: {t}" for t in sp["paid_sections"]]
        teasers.update({f"{tag.title()}: {k}": v for k, v in sp["teasers"].items()})

    meta = {"verdicts": verdicts, "paidSections": paid_sections,
            "teasers": teasers, "price": PRICES["horary"],
            "question": p["question"], "asked": f"{p['qDate']} {p['qTime']}"}
    rid = _save_report(uid, "", "horary", free_html, paid_html, meta,
                       paid=1 if entitled else 0)
    return {"reportId": rid, "paid": entitled, "meta": meta,
            "links": _links(rid, uid, entitled), "price": PRICES["horary"]}


# ---- daily reading (subscription) ----------------------------------------
def h_daily(uid: str, p: dict) -> dict:
    """daily_moon_prediction.compute_daily_moon_guide(pc, target_date, lat/lon/tz)."""
    from daily_moon_prediction import compute_daily_moon_guide
    chart = _chart_row(uid, p)
    pc = _precompute(chart)
    target = _as_date(p.get("date") or date.today().isoformat())

    subscribed = _entitled(uid, "daily")
    free_left = _free_daily_left(uid)
    if not subscribed and free_left <= 0:
        return {"locked": True, "price": PRICES["subscription"],
                "message": "Your 3 free daily readings are used. "
                           "Subscribe for a personalised reading every morning."}

    data = compute_daily_moon_guide(pc, target, latitude=chart["lat"],
                                    longitude=chart["lon"], timezone=chart["tz"])
    import astro_voice as V
    vctx = V.context_from_pc(pc, name=chart["name"] or "Seeker",
                             place=chart["place"] or "", tob=chart["tob"])
    if isinstance(data, dict):
        data["personal_note"] = V.strip_machinery(V.humanise(
            V.chart_opening(vctx))).replace("<p>", "").replace("</p>", "")
    if not subscribed:
        _use_free_daily(uid)
    return {"locked": False, "date": target.isoformat(), "subscribed": subscribed,
            "freeDaysLeft": max(0, free_left - (0 if subscribed else 1)),
            "reading": data}


def _free_daily_left(uid: str) -> int:
    with closing(db()) as con:
        n = con.execute("SELECT COUNT(*) c FROM orders WHERE user_id=? AND item='daily_free'",
                        (uid,)).fetchone()["c"]
    return max(0, 3 - n)


def _use_free_daily(uid: str) -> None:
    with closing(db()) as con:
        con.execute("INSERT INTO orders (id,user_id,item,amount,status,created_at)"
                    " VALUES (?,?,'daily_free',0,'paid',?)",
                    ("DF-" + uuid.uuid4().hex[:8], uid, now_iso()))
        con.commit()


# ---- kundali matching -----------------------------------------------------
def h_match(uid: str, p: dict) -> dict:
    """kundali_match.build_person_chart + match_kundali + write_kundali_match_report"""
    import astro_split as SP
    import astro_voice as V
    from kundali_match import build_person_chart, match_kundali
    from kundali_match_report import write_kundali_match_report

    def person(pre: str) -> dict:
        return {"name": p.get(pre + "Name") or pre.title(), "dob": p[pre + "Dob"],
                "birth_time": p[pre + "Tob"], "latitude": float(p[pre + "Lat"]),
                "longitude": float(p[pre + "Lon"]), "timezone": float(p.get(pre + "Tz", 5.5)),
                "place_name": p.get(pre + "Place", ""),
                "gender": 0 if pre == "groom" else 1}

    g, b = person("groom"), person("bride")
    gpc = build_person_chart(**g)
    bpc = build_person_chart(**b)
    result = match_kundali(groom=gpc, bride=bpc, method=p.get("method", "North"),
                           groom_name=g["name"], bride_name=b["name"],
                           groom_dob=g["dob"], bride_dob=b["dob"])

    d = REPORTS / ("match_" + uuid.uuid4().hex[:8]); d.mkdir(parents=True, exist_ok=True)
    out = d / "match.html"
    write_kundali_match_report(
        result=result,
        groom_meta={"name": g["name"], "dob": g["dob"], "tob": g["birth_time"], "place": g["place_name"]},
        bride_meta={"name": b["name"], "dob": b["dob"], "tob": b["birth_time"], "place": b["place_name"]},
        out_path=out)
    html = V.personalise(out.read_text(encoding="utf-8", errors="ignore"),
                         {"name": f"{g['name']} & {b['name']}", "dob": g["dob"],
                          "place": g["place_name"], "tob": g["birth_time"]}, "chart")

    ashta = result.get("ashtakoota") or {}
    total = ashta.get("total_guna")
    # Free: the headline verdict and the 36-guna table. Paid: the dosha analysis,
    # remedies, D9 synastry and the numerology protocol.
    split = SP.split_report(html, ("kundali milan", "final verdict",
                                   "layer 1", "ashtakoota", "prepared for"),
                            locked_note="Your guna score is above. Unlock the dosha analysis "
                                        "and its remedies, the Navamsha (D9) synastry and the "
                                        "full numerology compatibility protocol.")
    entitled = _entitled(uid, "kundali_match")
    vd = result.get("verdict") or {}
    doshas = result.get("doshas") or {}
    active = [d.get("name") or d.get("label") for d in (doshas.get("items") or [])
              if d.get("active")]
    meta = {"total": total, "maxGuna": ashta.get("max_guna"),
            "band": ashta.get("band"), "bandPlain": ashta.get("band_plain"),
            "verdict": vd.get("verdict"), "headline": vd.get("headline"),
            "d9Verdict": vd.get("d9_verdict"),
            "koots": [{"label": k.get("label"), "score": k.get("score"),
                       "max": k.get("max"), "ok": k.get("ok")}
                      for k in (ashta.get("koots") or [])],
            "stars": {"groom": ashta.get("groom_nakshatra"), "bride": ashta.get("bride_nakshatra"),
                      "groomMoon": ashta.get("groom_moon_sign"), "brideMoon": ashta.get("bride_moon_sign")},
            "activeDoshas": active, "doshaCount": doshas.get("active_count"),
            "blocking": doshas.get("has_blocking"),
            "paidSections": split["paid_sections"], "teasers": split["teasers"],
            "price": PRICES["kundali_match"],
            "couple": {"groom": g["name"], "bride": b["name"]}}
    rid = _save_report(uid, "", "kundali_match", split["free_html"], split["paid_html"],
                       meta, paid=1 if entitled else 0)
    return {"reportId": rid, "paid": entitled, "meta": meta,
            "links": _links(rid, uid, entitled), "price": PRICES["kundali_match"]}


# ---- muhurat --------------------------------------------------------------
def h_muhurat_events(uid: str, p: dict) -> dict:
    from muhurat_checker import event_catalog
    return {"events": event_catalog()}


def h_muhurat(uid: str, p: dict) -> dict:
    """muhurat_checker.check_muhurat — 17 event types, panchang + chart overlay."""
    from muhurat_checker import check_muhurat
    pc: dict = {}
    if p.get("dob") and p.get("tob"):
        pc = _precompute(_chart_row(uid, p))
    res = check_muhurat(
        event_id=p["eventId"], target=_as_date(p["date"]), pc=pc,
        latitude=float(p.get("lat", 28.6)), longitude=float(p.get("lon", 77.2)),
        timezone=float(p.get("tz", 5.5)), place_name=p.get("place", "BirthPlace"),
        suggest_alternatives=True)
    entitled = _entitled(uid, "muhurat") or _entitled(uid, "subscription")
    # Free: is this day workable at all, in one line. Paid: the checks, the
    # hour-by-hour windows, the chart notes and better alternative dates.
    free = {k: res.get(k) for k in ("available", "error", "verdict", "headline",
                                    "summary", "event_label", "event_plain",
                                    "target_date", "needs_partner_chart")}
    free["checkCount"] = len(res.get("checks") or [])
    free["alternativeCount"] = len(res.get("alternatives") or [])
    return {"paid": entitled, "date": p["date"], "eventId": p["eventId"],
            "summary": free,
            "detail": {k: res.get(k) for k in ("checks", "chart_notes", "panchang",
                                               "day_windows", "alternatives")} if entitled else None,
            "price": PRICES["muhurat"]}


# ---- birth-time rectification --------------------------------------------
def h_btr(uid: str, p: dict) -> dict:
    """btr_rectify.rectify_birth_time — coarse ±90min then 30-second D60 scan."""
    from btr_rectify import rectify_birth_time
    # btr_rectify.parse_events_from_form expects bare EVENT_SPECS keys
    # ("first_job", "marriage", …) — tolerate the btr_-prefixed form names too.
    fields = {k[4:] if k.startswith("btr_") else k: v
              for k, v in (p.get("events") or {}).items() if v}
    res = rectify_birth_time(
        client_name=p.get("name", "Seeker"), dob=p["dob"], birth_time=p["tob"],
        latitude=float(p["lat"]), longitude=float(p["lon"]),
        timezone=float(p.get("tz", 5.5)), place_name=p.get("place", ""),
        gender=int(p.get("gender", 0)), event_fields=fields,
        custom_events=p.get("customEvents", ""), auto_apply=False)
    entitled = _entitled(uid, "btr")
    off = res.get("offset_minutes")
    # Free: we tell them whether their stated time survives scrutiny, and by how
    # much it moves — but the corrected time itself is the paid answer.
    return {"paid": entitled,
            "skipped": res.get("skipped"), "reason": res.get("reason"),
            "trialTime": res.get("trial_time"),
            "confidence": res.get("confidence"),
            "eventsUsed": res.get("events_used"),
            "trialScore": res.get("trial_score"), "bestScore": res.get("best_score"),
            "trialVerdict": res.get("trial_verdict"),
            "lagnaTrial": res.get("lagna_trial"),
            # a rising-sign change is the headline finding — say so for free
            "changesLagna": (bool(res.get("lagna_trial") and res.get("lagna_best")
                                  and str(res["lagna_trial"]).split()[0]
                                  != str(res["lagna_best"]).split()[0])),
            "movesBy": (None if off is None else
                        ("under a minute" if abs(off) < 1 else
                         f"about {abs(int(off))} minute{'s' if abs(int(off)) != 1 else ''}")),
            "correctedTime": res.get("corrected_time") if entitled else None,
            "offsetMinutes": off if entitled else None,
            "suggestedTime": res.get("suggested_time") if entitled else None,
            "lagnaBest": res.get("lagna_best") if entitled else None,
            "eventResults": res.get("best_event_results") if entitled else None,
            "perEventWins": res.get("per_event_wins") if entitled else None,
            "funnel": res.get("funnel_best") if entitled else None,
            "fineScanUsed": res.get("fine_scan_used"),
            "message": res.get("message") if entitled else None,
            "price": PRICES["btr"]}


def h_future_event(uid: str, p: dict) -> dict:
    """future_event_timing.predict_next_event(**birth data, event_type=...)"""
    from future_event_timing import predict_next_event
    chart = _chart_row(uid, p)
    res = predict_next_event(
        client_name=chart["name"] or "Seeker", dob=chart["dob"],
        birth_time=chart["tob"], latitude=chart["lat"], longitude=chart["lon"],
        timezone=chart["tz"], place_name=chart["place"] or "",
        gender=chart["gender"], event_type=p["eventType"],
        consultation_date=p.get("consultationDate", ""),
    )
    entitled = _entitled(uid, "future_event")
    return {
        "paid": entitled, "eventType": p["eventType"],
        "promised": res.get("promised"), "timingAvailable": res.get("timing_available"),
        "window": res.get("next_window") if entitled else None,
        "alternates": res.get("alternates") if entitled else None,
        "remedies": res.get("remedies") if entitled else None,
        "error": res.get("error"), "price": PRICES["future_event"],
    }


HANDLERS = {
    "chart_summary": h_chart_summary,
    "muhurat_events": h_muhurat_events,
    "btr": h_btr,
    "numerology": h_numerology,
    "full_report": h_full_report,
    "horary": h_horary,
    "daily": h_daily,
    "kundali_match": h_match,
    "muhurat": h_muhurat,
    "future_event": h_future_event,
}


# ===========================================================================
# 7. Routes
# ===========================================================================
class BirthIn(BaseModel):
    name: str = Field(default="Seeker", max_length=80)
    dob: str
    tob: str
    place: str = ""
    lat: float
    lon: float
    tz: float = 5.5
    gender: int = 0
    question: str = ""


class JobIn(BaseModel):
    kind: str
    payload: Dict[str, Any] = {}


@app.post("/api/astro/job")
async def submit_job(body: JobIn, uid: str = Depends(current_user)):
    if body.kind not in HANDLERS:
        raise HTTPException(400, f"unknown kind; try {sorted(HANDLERS)}")
    job = await Q.submit(uid, body.kind, body.payload)
    return JSONResponse(Q.snapshot(job))


@app.get("/api/astro/job/{jid}")
async def job_status(jid: str, uid: str = Depends(current_user)):
    job = Q.jobs.get(jid)
    if not job or job.uid != uid:
        raise HTTPException(404, "no such job")
    return JSONResponse(Q.snapshot(job))


@app.delete("/api/astro/job/{jid}")
async def job_cancel(jid: str, uid: str = Depends(current_user)):
    await Q.cancel(jid, uid)
    return {"ok": True}


@app.get("/api/astro/reports")
async def my_reports(uid: str = Depends(current_user)):
    with closing(db()) as con:
        rows = con.execute(
            "SELECT id,kind,paid,meta,created_at FROM reports WHERE user_id=?"
            " ORDER BY created_at DESC LIMIT 50", (uid,)).fetchall()
    return [{"reportId": r["id"], "kind": r["kind"], "paid": bool(r["paid"]),
             "createdAt": r["created_at"],
             "meta": json.loads(r["meta"] or "{}"),
             "links": _links(r["id"], uid, bool(r["paid"]))} for r in rows]


@app.get("/api/astro/prices")
async def prices():
    return {"prices": PRICES, "subscriptionIncludes":
            {"daily": True, "horaryPerMonth": SUB_HORARY_ALLOWANCE, "muhurat": "unlimited"}}


@app.get("/api/astro/queue")
async def queue_stats():
    return {"maxConcurrent": MAX_CONCURRENT, "activeJobs": Q.active,
            "waiting": len(Q.waiting),
            "avgSeconds": {k: round(Q.avg(k), 1) for k in HANDLERS}}


@app.get("/health")
async def health():
    return {"ok": True, "slots": MAX_CONCURRENT, "active": Q.active,
            "waiting": len(Q.waiting), "db": DB_PATH.exists()}
