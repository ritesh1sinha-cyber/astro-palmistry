"""
Database layer — SQLAlchemy Core over the canonical schema.

Postgres in production, SQLite for a laptop. Endpoints are sync `def` so
FastAPI runs them in its threadpool; that keeps the connection handling simple
and is comfortably fast for this workload (all the heavy lifting is in workers).
"""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

from .config import S

_engine: Optional[Engine] = None


from core.errors import gender_code


def engine() -> Engine:
    global _engine
    if _engine is None:
        url = S.database_url
        print(f"[db] DATABASE_URL={url}", flush=True)
        kw: dict[str, Any] = {"future": True, "pool_pre_ping": True}
        if url.startswith("postgres"):
            # pool sized per API replica; 20 × 4 replicas stays well under
            # Postgres' default 100 connections, leaving room for workers.
            kw.update(poolclass=QueuePool, pool_size=10, max_overflow=10,
                      pool_recycle=1800)
        else:
            kw.update(connect_args={"check_same_thread": False})
        _engine = create_engine(url, **kw)
        if not url.startswith("postgres"):
            with _engine.begin() as c:
                c.exec_driver_sql("PRAGMA journal_mode=WAL")
    return _engine


@contextmanager
def tx() -> Iterator[Any]:
    """One transaction. Commits on success, rolls back on any exception."""
    with engine().begin() as conn:
        yield conn


def now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# schema bootstrap
# ---------------------------------------------------------------------------
SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY, google_sub TEXT UNIQUE, email TEXT UNIQUE NOT NULL,
  name TEXT, picture TEXT, phone TEXT, locale TEXT DEFAULT 'en',
  status TEXT DEFAULT 'active', credits INTEGER DEFAULT 0,
  created_at TEXT, last_seen_at TEXT, deleted_at TEXT);
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL, token_hash TEXT UNIQUE NOT NULL,
  created_at TEXT, expires_at TEXT, revoked_at TEXT, ip TEXT, user_agent TEXT);
CREATE TABLE IF NOT EXISTS charts (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL, label TEXT, person_name TEXT,
  dob TEXT NOT NULL, tob TEXT NOT NULL, tz_offset REAL NOT NULL,
  lat REAL NOT NULL, lon REAL NOT NULL, place TEXT, gender INTEGER DEFAULT 0,
  chart_hash TEXT NOT NULL, is_primary INTEGER DEFAULT 0, created_at TEXT);
CREATE UNIQUE INDEX IF NOT EXISTS ux_charts_user_hash ON charts(user_id, chart_hash);
CREATE TABLE IF NOT EXISTS precomputes (
  chart_hash TEXT NOT NULL, engine_version TEXT NOT NULL, payload TEXT,
  payload_key TEXT, bytes INTEGER, hits INTEGER DEFAULT 0,
  created_at TEXT, last_used_at TEXT, PRIMARY KEY (chart_hash, engine_version));
CREATE TABLE IF NOT EXISTS orders (
  id TEXT PRIMARY KEY, public_id TEXT UNIQUE NOT NULL, user_id TEXT NOT NULL,
  item TEXT NOT NULL, ref_id TEXT, amount_paise INTEGER NOT NULL,
  currency TEXT DEFAULT 'INR', status TEXT DEFAULT 'created', gateway TEXT,
  gateway_order_id TEXT, gateway_payment_id TEXT, idempotency_key TEXT UNIQUE,
  created_at TEXT, paid_at TEXT, refunded_at TEXT);
CREATE TABLE IF NOT EXISTS payment_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT, gateway TEXT,
  event_type TEXT, signature_ok INTEGER DEFAULT 0, payload TEXT, received_at TEXT);
CREATE TABLE IF NOT EXISTS entitlements (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL, item TEXT NOT NULL, ref_id TEXT,
  source TEXT NOT NULL, order_id TEXT, granted_at TEXT, expires_at TEXT, revoked_at TEXT);
CREATE TABLE IF NOT EXISTS subscriptions (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL, plan TEXT, status TEXT DEFAULT 'active',
  current_period_end TEXT NOT NULL, cancel_at TEXT, gateway_sub_id TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS credit_ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, delta INTEGER NOT NULL,
  reason TEXT NOT NULL, ref_id TEXT, balance_after INTEGER NOT NULL, created_at TEXT);
CREATE TABLE IF NOT EXISTS usage_counters (
  user_id TEXT NOT NULL, kind TEXT NOT NULL, period TEXT NOT NULL,
  used INTEGER DEFAULT 0, updated_at TEXT, PRIMARY KEY (user_id, kind, period));
CREATE TABLE IF NOT EXISTS report_generation_stats (
  kind TEXT PRIMARY KEY, count INTEGER NOT NULL DEFAULT 0, updated_at TEXT);
CREATE TABLE IF NOT EXISTS page_view_stats (
  path TEXT PRIMARY KEY, count INTEGER NOT NULL DEFAULT 0, updated_at TEXT);
CREATE TABLE IF NOT EXISTS reports (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL, chart_id TEXT, kind TEXT NOT NULL,
  paid INTEGER DEFAULT 0, free_key TEXT, paid_key TEXT, meta TEXT DEFAULT '{}',
  engine_version TEXT, created_at TEXT, expires_at TEXT);
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY, public_id TEXT NOT NULL, user_id TEXT, kind TEXT NOT NULL,
  status TEXT DEFAULT 'queued', priority INTEGER DEFAULT 5, attempts INTEGER DEFAULT 0,
  chart_id TEXT, report_id TEXT, payload TEXT, error TEXT, worker_id TEXT,
  duration_ms INTEGER, created_at TEXT, started_at TEXT, finished_at TEXT);
CREATE INDEX IF NOT EXISTS ix_jobs_public ON jobs(public_id);
CREATE TABLE IF NOT EXISTS enquiries (
  id TEXT PRIMARY KEY, user_id TEXT, name TEXT, phone TEXT, email TEXT,
  message TEXT, status TEXT DEFAULT 'new', created_at TEXT);
CREATE TABLE IF NOT EXISTS waitlist (email TEXT PRIMARY KEY, topic TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS promo_codes (
  id TEXT PRIMARY KEY, code TEXT UNIQUE NOT NULL,
  item TEXT NOT NULL DEFAULT 'bundle_all',
  max_redemptions INTEGER NOT NULL CHECK (max_redemptions > 0),
  redeemed_count INTEGER NOT NULL DEFAULT 0,
  active INTEGER NOT NULL DEFAULT 1, expires_at TEXT, note TEXT, created_at TEXT,
  CHECK (redeemed_count <= max_redemptions));
CREATE TABLE IF NOT EXISTS promo_redemptions (
  id TEXT PRIMARY KEY, code_id TEXT NOT NULL, user_id TEXT NOT NULL,
  item TEXT NOT NULL, redeemed_at TEXT);
CREATE UNIQUE INDEX IF NOT EXISTS ux_promo_once
  ON promo_redemptions(code_id, user_id);
CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT, actor TEXT, action TEXT NOT NULL,
  subject TEXT, detail TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS chat_messages (
  id TEXT PRIMARY KEY, report_id TEXT NOT NULL, user_id TEXT NOT NULL,
  role TEXT NOT NULL, content TEXT NOT NULL, meta TEXT DEFAULT '{}',
  created_at TEXT);
CREATE INDEX IF NOT EXISTS ix_chat_report ON chat_messages(report_id, created_at);
"""


def init_schema() -> None:
    if S.is_postgres:
        sql = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
        with engine().begin() as c:
            c.exec_driver_sql(sql)
    else:
        with engine().begin() as c:
            for stmt in SQLITE_SCHEMA.split(";"):
                if stmt.strip():
                    c.exec_driver_sql(stmt)


def extend_partitions() -> None:
    """Roll monthly partitions forward. No-op on SQLite."""
    if not S.is_postgres:
        return
    with engine().begin() as c:
        c.exec_driver_sql("SELECT extend_partitions()")


# ---------------------------------------------------------------------------
# helpers used across the app
# ---------------------------------------------------------------------------
def chart_hash(dob: str, tob: str, lat: float, lon: float, tz: float) -> str:
    key = f"{dob}|{tob}|{round(float(lat), 4)}|{round(float(lon), 4)}|{tz}"
    return hashlib.sha256(key.encode()).hexdigest()


def jrow(row) -> dict:
    return dict(row._mapping) if row is not None else {}


def jdump(v: Any) -> str:
    return json.dumps(v, default=str)


def jload(v: Any) -> Any:
    if v is None or isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(v)
    except (TypeError, ValueError):
        return v


# ---------------------------------------------------------------------------
# users & sessions
# ---------------------------------------------------------------------------
def upsert_user(*, email: str, name: str = "", picture: str = "",
                google_sub: Optional[str] = None) -> dict:
    with tx() as c:
        row = c.execute(text("SELECT * FROM users WHERE email = :e"),
                        {"e": email}).fetchone()
        if row:
            c.execute(text("UPDATE users SET last_seen_at = :t,"
                           " name = COALESCE(NULLIF(:n,''), name),"
                           " picture = COALESCE(NULLIF(:p,''), picture),"
                           " google_sub = COALESCE(:g, google_sub)"
                           " WHERE id = :id"),
                      {"t": now(), "n": name, "p": picture, "g": google_sub,
                       "id": row._mapping["id"]})
            return jrow(c.execute(text("SELECT * FROM users WHERE id = :id"),
                                  {"id": row._mapping["id"]}).fetchone())
        uid = new_id()
        c.execute(text("INSERT INTO users (id, google_sub, email, name, picture,"
                       " credits, created_at, last_seen_at)"
                       " VALUES (:id,:g,:e,:n,:p,0,:t,:t)"),
                  {"id": uid, "g": google_sub, "e": email, "n": name,
                   "p": picture, "t": now()})
        return jrow(c.execute(text("SELECT * FROM users WHERE id = :id"),
                              {"id": uid}).fetchone())


def create_session(user_id: str, *, ip: str = "", ua: str = "") -> str:
    raw = secrets.token_urlsafe(32)
    with tx() as c:
        c.execute(text("INSERT INTO sessions (id,user_id,token_hash,created_at,"
                       "expires_at,ip,user_agent) VALUES (:i,:u,:h,:c,:e,:ip,:ua)"),
                  {"i": new_id(), "u": user_id,
                   "h": hashlib.sha256(raw.encode()).hexdigest(),
                   "c": now(), "e": now() + timedelta(days=S.session_days),
                   "ip": ip or None, "ua": ua[:400]})
    return raw


def user_for_token(raw: str) -> Optional[dict]:
    h = hashlib.sha256(raw.encode()).hexdigest()
    with engine().connect() as c:
        row = c.execute(text(
            "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id"
            " WHERE s.token_hash = :h AND s.revoked_at IS NULL"
            "   AND s.expires_at > :now AND u.status = 'active'"),
            {"h": h, "now": now()}).fetchone()
    return jrow(row) if row else None


def revoke_session(raw: str) -> None:
    with tx() as c:
        c.execute(text("UPDATE sessions SET revoked_at = :t WHERE token_hash = :h"),
                  {"t": now(), "h": hashlib.sha256(raw.encode()).hexdigest()})


# ---------------------------------------------------------------------------
# charts + precompute cache
# ---------------------------------------------------------------------------
def get_or_create_chart(user_id: str, p: dict) -> dict:
    h = chart_hash(p["dob"], p["tob"], p["lat"], p["lon"], p.get("tz", 5.5))
    with tx() as c:
        row = c.execute(text("SELECT * FROM charts WHERE user_id=:u AND chart_hash=:h"),
                        {"u": user_id, "h": h}).fetchone()
        if row:
            return jrow(row)
        cid = new_id()
        c.execute(text("INSERT INTO charts (id,user_id,label,person_name,dob,tob,"
                       "tz_offset,lat,lon,place,gender,chart_hash,created_at)"
                       " VALUES (:i,:u,:l,:pn,:dob,:tob,:tz,:lat,:lon,:pl,:g,:h,:t)"),
                  {"i": cid, "u": user_id, "l": p.get("label"),
                   "pn": p.get("name"), "dob": p["dob"], "tob": p["tob"],
                   "tz": p.get("tz", 5.5), "lat": p["lat"], "lon": p["lon"],
                   "pl": p.get("place"), "g": gender_code(p.get("gender")),
                   "h": h, "t": now()})
        return jrow(c.execute(text("SELECT * FROM charts WHERE id=:i"),
                             {"i": cid}).fetchone())


def precompute_get(chart_hash_: str) -> Optional[dict]:
    with tx() as c:
        row = c.execute(text("SELECT payload, payload_key FROM precomputes"
                             " WHERE chart_hash=:h AND engine_version=:v"),
                        {"h": chart_hash_, "v": S.engine_version}).fetchone()
        if not row:
            return None
        c.execute(text("UPDATE precomputes SET hits = hits + 1, last_used_at = :t"
                       " WHERE chart_hash=:h AND engine_version=:v"),
                  {"t": now(), "h": chart_hash_, "v": S.engine_version})
    m = row._mapping
    if m["payload"] is not None:
        return jload(m["payload"])
    if m["payload_key"]:
        from .store import store
        return json.loads(store().get(m["payload_key"]).decode())
    return None


def precompute_put(chart_hash_: str, payload: dict) -> None:
    blob = jdump(payload)
    inline, key = (blob, None) if len(blob) < 400_000 else (None, None)
    if inline is None:
        from .store import store
        key = f"precompute/{S.engine_version}/{chart_hash_}.json"
        store().put(key, blob.encode(), "application/json")
    with tx() as c:
        c.execute(text(
            "INSERT INTO precomputes (chart_hash,engine_version,payload,payload_key,"
            "bytes,created_at,last_used_at) VALUES (:h,:v,:p,:k,:b,:t,:t)"
            + (" ON CONFLICT (chart_hash, engine_version) DO NOTHING"
               if S.is_postgres else " ON CONFLICT DO NOTHING")),
            {"h": chart_hash_, "v": S.engine_version, "p": inline, "k": key,
             "b": len(blob), "t": now()})


# ---------------------------------------------------------------------------
# jobs (durable mirror of the Redis queue)
# ---------------------------------------------------------------------------
def job_insert(*, public_id: str, user_id: str, kind: str, payload: dict,
               priority: int) -> str:
    jid = new_id()
    with tx() as c:
        c.execute(text("INSERT INTO jobs (id,public_id,user_id,kind,status,priority,"
                       "payload,created_at) VALUES (:i,:p,:u,:k,'queued',:pr,:pl,:t)"),
                  {"i": jid, "p": public_id, "u": user_id, "k": kind,
                   "pr": priority, "pl": jdump(payload), "t": now()})
    return jid


def job_update(public_id: str, **fields) -> None:
    if not fields:
        return
    if "payload" in fields:
        fields["payload"] = jdump(fields["payload"])
    sets = ", ".join(f"{k} = :{k}" for k in fields)
    with tx() as c:
        c.execute(text(f"UPDATE jobs SET {sets} WHERE public_id = :pid"),
                  {**fields, "pid": public_id})


def job_get(public_id: str) -> Optional[dict]:
    with engine().connect() as c:
        row = c.execute(text("SELECT * FROM jobs WHERE public_id = :p"),
                        {"p": public_id}).fetchone()
    if not row:
        return None
    d = jrow(row)
    d["payload"] = jload(d.get("payload"))
    return d


# ---------------------------------------------------------------------------
# reports
# ---------------------------------------------------------------------------
def report_insert(*, user_id: str, chart_id: Optional[str], kind: str,
                  free_key: str, paid_key: str, meta: dict, paid: bool) -> str:
    rid = new_id()
    exp = now() + timedelta(days=S.report_retention_days)
    with tx() as c:
        c.execute(text("INSERT INTO reports (id,user_id,chart_id,kind,paid,free_key,"
                       "paid_key,meta,engine_version,created_at,expires_at)"
                       " VALUES (:i,:u,:c,:k,:paid,:f,:p,:m,:v,:t,:e)"),
                  {"i": rid, "u": user_id, "c": chart_id, "k": kind,
                   "paid": bool(paid), "f": free_key, "p": paid_key,
                   "m": jdump(meta), "v": S.engine_version, "t": now(), "e": exp})
    return rid


def report_get(report_id: str, user_id: Optional[str] = None) -> Optional[dict]:
    q = "SELECT * FROM reports WHERE id = :i"
    args: dict[str, Any] = {"i": report_id}
    if user_id:
        q += " AND user_id = :u"
        args["u"] = user_id
    with engine().connect() as c:
        row = c.execute(text(q), args).fetchone()
    if not row:
        return None
    d = jrow(row)
    d["meta"] = jload(d.get("meta")) or {}
    d["paid"] = bool(d.get("paid"))
    return d


def reports_for_user(user_id: str, limit: int = 50) -> list[dict]:
    with engine().connect() as c:
        rows = c.execute(text("SELECT * FROM reports WHERE user_id = :u"
                              " ORDER BY created_at DESC LIMIT :l"),
                         {"u": user_id, "l": limit}).fetchall()
    out = []
    for r in rows:
        d = jrow(r)
        d["meta"] = jload(d.get("meta")) or {}
        d["paid"] = bool(d.get("paid"))
        out.append(d)
    return out


def report_mark_paid(report_id: str) -> None:
    with tx() as c:
        c.execute(text("UPDATE reports SET paid = :p WHERE id = :i"),
                  {"p": True, "i": report_id})


def report_delete(report_id: str, user_id: str) -> bool:
    """Remove a report row owned by user_id. Returns True if a row was deleted."""
    with tx() as c:
        res = c.execute(text("DELETE FROM reports WHERE id = :i AND user_id = :u"),
                        {"i": report_id, "u": user_id})
    return (res.rowcount or 0) > 0


# ---------------------------------------------------------------------------
# chat (paid follow-up against a report's facts.json)
# ---------------------------------------------------------------------------
def chat_append(report_id: str, user_id: str, role: str, content: str,
                meta: Optional[dict] = None) -> dict:
    mid = new_id()
    with tx() as c:
        c.execute(text(
            "INSERT INTO chat_messages (id, report_id, user_id, role, content, meta, created_at)"
            " VALUES (:i, :r, :u, :role, :c, :m, :t)"),
            {"i": mid, "r": report_id, "u": user_id, "role": role,
             "c": content, "m": jdump(meta or {}), "t": now()})
    return {"id": mid, "role": role, "content": content}


def chat_history(report_id: str, user_id: str, *, limit: int = 20) -> list[dict]:
    with tx() as c:
        rows = c.execute(text(
            "SELECT id, role, content, meta, created_at FROM chat_messages"
            " WHERE report_id = :r AND user_id = :u"
            " ORDER BY created_at DESC LIMIT :n"),
            {"r": report_id, "u": user_id, "n": int(limit)}).mappings().all()
    out = []
    for r in reversed(list(rows)):
        d = dict(r)
        if isinstance(d.get("meta"), str):
            try:
                d["meta"] = json.loads(d["meta"] or "{}")
            except Exception:  # noqa: BLE001
                d["meta"] = {}
        out.append(d)
    return out
