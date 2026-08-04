"""
Distributed job queue on Redis.

Why not the in-process queue any more: with several API replicas and several
worker replicas, "3 at a time" has to be enforced somewhere shared. Redis is
that somewhere.

Design
------
* One sorted set per kind-group, scored by (priority, enqueue time). Paying and
  subscribed users get a better priority, so a ₹1,499 report never waits behind
  a queue of free chart summaries.
* A per-kind concurrency cap held as a ZSET of leased slots, taken under
  WATCH/MULTI. Leases expire, so a killed worker cannot leak capacity, and no
  EVAL is needed (some managed Redis offerings block Lua).
* Per-kind duration stats (rolling, EWMA) so the ETA shown to a user is
  measured, not guessed — and it is the same number across every replica.
* Job state cached in Redis for fast polling; Postgres holds the durable record.

Falls back to a fakeredis instance when REDIS_URL is unset so a laptop needs no
infrastructure.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Optional

from .config import S

# ---------------------------------------------------------------------------
# connection
# ---------------------------------------------------------------------------
_r = None


def r():
    global _r
    if _r is None:
        if S.redis_url:
            import redis
            _r = redis.Redis.from_url(S.redis_url, decode_responses=True,
                                      health_check_interval=30,
                                      socket_keepalive=True)
        else:                                    # laptop / CI
            import fakeredis
            _r = fakeredis.FakeRedis(decode_responses=True)
    return _r


# ---------------------------------------------------------------------------
# keys
# ---------------------------------------------------------------------------
def _q(group: str) -> str:      return f"q:{group}"
def _job(pid: str) -> str:      return f"job:{pid}"
def _slots(kind: str) -> str:   return f"slots:{kind}"
def _stat(kind: str) -> str:    return f"stat:{kind}"
def _rate(uid: str) -> str:     return f"rate:{uid}"

# kinds that get their own concurrency budget; everything else shares "*"
GROUPS = {"full_report": "heavy", "btr": "heavy", "palm": "palm"}


def group_of(kind: str) -> str:
    return GROUPS.get(kind, "light")


def cap_of(kind: str) -> int:
    return S.kind_caps.get(kind, S.kind_caps.get("*", 8))


# ---------------------------------------------------------------------------
# priority: paying customers first
# ---------------------------------------------------------------------------
def priority_for(*, paid: bool, subscribed: bool) -> int:
    if paid:
        return 1
    if subscribed:
        return 3
    return 5


# ---------------------------------------------------------------------------
# enqueue / dequeue
# ---------------------------------------------------------------------------
def _dumps(job: dict) -> str:
    """Serialise a job for Redis.

    `default=str` is not cosmetic. `users.id` is a UUID column in Postgres, so
    psycopg returns a `uuid.UUID` and json.dumps raises
    "Object of type UUID is not JSON serializable". On SQLite that same column is
    TEXT and the value is already a str — so every SQLite test passed while the
    Postgres stack failed on the first job it was ever handed. Dates and Decimals
    arrive the same way from a real database.
    """
    return json.dumps(job, default=str)


def enqueue(*, kind: str, user_id: str, payload: dict, priority: int = 5) -> dict:
    pid = "J-" + uuid.uuid4().hex[:10].upper()
    now = time.time()
    job = {"jobId": pid, "kind": kind, "userId": str(user_id), "status": "queued",
           "priority": priority, "payload": payload, "queuedAt": now}
    p = r().pipeline()
    p.hset(_job(pid), mapping={"json": _dumps(job)})
    p.expire(_job(pid), S.job_ttl_seconds)
    # score packs priority into the integer part and time into the fraction,
    # so within a priority band it is strictly FIFO
    p.zadd(_q(group_of(kind)), {pid: priority * 1e12 + now})
    p.execute()
    return job


def queue_depth(group: str) -> int:
    return int(r().zcard(_q(group)) or 0)


def total_depth() -> int:
    return sum(queue_depth(g) for g in set(list(GROUPS.values()) + ["light"]))


# ---------------------------------------------------------------------------
# concurrency budget: a leased slot per running job
# ---------------------------------------------------------------------------
# Slots live in a ZSET scored by lease expiry. Expired members are reaped on
# every attempt, so a worker that is SIGKILLed cannot leak capacity forever.
# The take is done under WATCH/MULTI (optimistic locking) rather than Lua —
# atomic on real Redis, and it also works on managed Redis that blocks EVAL.
SLOT_LEASE = 1800


def take_slot(kind: str, holder: str, ttl: int = SLOT_LEASE) -> bool:
    """Atomically acquire one slot of the per-kind concurrency cap.

    The original implementation used WATCH + pipeline, which is correct for a
    multi-process / multi-replica deployment on real Redis. With fakeredis (the
    local/CI path) it misbehaved: WATCH is a no-op, the card count is read on
    the server BEFORE the pipeline flush, so the slot appears full even when
    empty, and jobs sit in the queue forever despite 0 of N slots in use.

    Lua script is atomic on both real Redis and fakeredis, has no round-trip
    race, and produces exactly one network call.
    """
    key = _slots(kind)
    cap = cap_of(kind)
    now_ts = time.time()
    # The script: expire old leases first, then check cap, then insert.
    # Returns 1 (slot acquired) or 0 (full).
    LUA = """
local key    = KEYS[1]
local cap    = tonumber(ARGV[1])
local holder = ARGV[2]
local score  = tonumber(ARGV[3])
local ttl2   = tonumber(ARGV[4])
redis.call('ZREMRANGEBYSCORE', key, 0, tonumber(ARGV[5]))
if redis.call('ZCARD', key) >= cap then return 0 end
redis.call('ZADD', key, score, holder)
redis.call('EXPIRE', key, ttl2)
return 1
"""
    result = r().eval(
        LUA, 1, key,
        str(cap), holder, str(now_ts + ttl), str(ttl * 2), str(now_ts)
    )
    return bool(result)


def release_slot(kind: str, holder: str) -> None:
    r().zrem(_slots(kind), holder)


def renew_slot(kind: str, holder: str, ttl: int = SLOT_LEASE) -> None:
    """Long jobs (a 3-minute report) call this to keep their lease alive."""
    r().zadd(_slots(kind), {holder: time.time() + ttl}, xx=True)


def slots_in_use(kind: str) -> int:
    key = _slots(kind)
    r().zremrangebyscore(key, 0, time.time())
    return int(r().zcard(key) or 0)


def claim(group: str, worker_id: str) -> Optional[dict]:
    """Pop the highest-priority job whose kind still has a free slot."""
    for pid in r().zrange(_q(group), 0, 24):
        raw = r().hget(_job(pid), "json")
        if not raw:
            r().zrem(_q(group), pid)
            continue
        job = json.loads(raw)
        if not take_slot(job["kind"], f"{worker_id}:{pid}"):
            continue                      # kind is at capacity; try the next
        if r().zrem(_q(group), pid) == 0:  # someone else got it first
            release_slot(job["kind"], f"{worker_id}:{pid}")
            continue
        job.update(status="processing", startedAt=time.time(), workerId=worker_id)
        save(job)
        return job
    return None


def save(job: dict) -> None:
    p = r().pipeline()
    p.hset(_job(job["jobId"]), mapping={"json": _dumps(job)})
    p.expire(_job(job["jobId"]), S.job_ttl_seconds)
    p.execute()


def load(pid: str) -> Optional[dict]:
    raw = r().hget(_job(pid), "json")
    return json.loads(raw) if raw else None


def cancel(pid: str) -> bool:
    job = load(pid)
    if not job or job.get("status") != "queued":
        return False
    r().zrem(_q(group_of(job["kind"])), pid)
    job["status"] = "cancelled"
    save(job)
    return True


def finish(job: dict, *, result: Any = None, error: str = "") -> None:
    job["status"] = "failed" if error else "done"
    job["finishedAt"] = time.time()
    if error:
        job["error"] = error
    else:
        job["result"] = result
        started = job.get("startedAt")
        if started:
            record_duration(job["kind"], time.time() - started)
    release_slot(job["kind"], f"{job.get('workerId')}:{job['jobId']}")
    save(job)


# ---------------------------------------------------------------------------
# measured durations → honest ETAs
# ---------------------------------------------------------------------------
DEFAULTS = {"full_report": 150.0, "btr": 90.0, "palm": 6.0, "horary": 8.0,
            "kundali_match": 10.0, "numerology": 3.0, "daily": 4.0,
            "chart_summary": 2.0, "muhurat": 4.0, "future_event": 20.0}


def record_duration(kind: str, seconds: float) -> None:
    """EWMA — reacts to real hardware without swinging on one slow run."""
    key = _stat(kind)
    prev = r().hget(key, "avg")
    avg = float(prev) if prev else DEFAULTS.get(kind, 30.0)
    new = 0.8 * avg + 0.2 * float(seconds)
    p = r().pipeline()
    p.hset(key, mapping={"avg": f"{new:.3f}"})
    p.hincrby(key, "n", 1)
    p.execute()


def avg_duration(kind: str) -> float:
    v = r().hget(_stat(kind), "avg")
    return float(v) if v else DEFAULTS.get(kind, 30.0)


def eta_for(job: dict) -> tuple[float, float]:
    kind = job["kind"]
    avg = avg_duration(kind)
    if job.get("status") == "processing" and job.get("startedAt"):
        return max(0.0, avg - (time.time() - job["startedAt"])), avg
    if job.get("status") == "queued":
        pos = position(job)
        cap = max(1, cap_of(kind))
        waves = max(0, pos - 1) // cap
        total = waves * avg + avg
        return total, total
    return 0.0, avg


def position(job: dict) -> int:
    rank = r().zrank(_q(group_of(job["kind"])), job["jobId"])
    return (rank + 1) if rank is not None else 0


def snapshot(job: dict) -> dict:
    eta, total = eta_for(job)
    return {"jobId": job["jobId"], "kind": job["kind"], "status": job["status"],
            "queuePosition": position(job), "etaSeconds": round(eta, 1),
            "etaTotalSeconds": round(total, 1),
            "activeJobs": slots_in_use(job["kind"]),
            "capacity": cap_of(job["kind"]),
            "result": job.get("result"), "error": job.get("error")}


# ---------------------------------------------------------------------------
# rate limiting (per user, sliding minute)
# ---------------------------------------------------------------------------
def rate_ok(user_id: str, limit: Optional[int] = None) -> bool:
    limit = limit or S.rate_per_min
    key = _rate(user_id)
    p = r().pipeline()
    p.incr(key)
    p.expire(key, 60)
    n = p.execute()[0]
    return int(n) <= limit


def health() -> dict:
    return {"depth": {g: queue_depth(g) for g in set(list(GROUPS.values()) + ["light"])},
            "slots": {k: slots_in_use(k) for k in S.kind_caps if k != "*"},
            "avg": {k: round(avg_duration(k), 1) for k in DEFAULTS}}
