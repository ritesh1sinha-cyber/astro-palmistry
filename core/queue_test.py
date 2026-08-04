#!/usr/bin/env python3
"""The queue must serialise what a REAL database hands it.

    python3 core/queue_test.py

This exists because of a bug that every other test in the repo was blind to.

`users.id` is a UUID column in Postgres, so psycopg returns a `uuid.UUID`.
`enqueue()` did a plain `json.dumps(job)`, which raises:

    TypeError: Object of type UUID is not JSON serializable

On SQLite that same column is TEXT and the value is already a `str`. Every suite
here runs on SQLite, so all of them passed while the Docker stack — Postgres —
failed on the very first reading it was ever asked to queue. The reported symptom
was a toast in the browser; the cause was two type systems disagreeing.

So the test does not use a database at all. It hands `enqueue()` the Python types
a real driver produces — UUID, datetime, date, Decimal — and asserts the job
survives a round trip. Redis is fakeredis when REDIS_URL is unset, so this needs
no services.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("APP_SECRET", "queue-test-only")
os.environ.pop("REDIS_URL", None)          # force fakeredis

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
# Drop this file's own directory from sys.path BEFORE importing anything.
# Running a script inside core/ puts core/ at sys.path[0], and core/queue.py then
# shadows the STDLIB `queue` module — which redis imports
# (`from queue import Empty, Full, LifoQueue`), so `import fakeredis` explodes
# with "attempted relative import with no known parent package". The package must
# be reached as core.queue, never as top-level queue.
sys.path[:] = [p for p in sys.path if p not in ("", ".", _HERE)]
sys.path.insert(0, _ROOT)

from core import queue as Q                                          # noqa: E402

PASS: list[str] = []
FAIL: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    (PASS if cond else FAIL).append(name)
    print(f"  {'ok  ' if cond else 'FAIL'} {name}"
          + (f"\n       {detail}" if detail and not cond else ""))


print("\n— the exact failure that reached a customer —")
uid = uuid.uuid4()
try:
    job = Q.enqueue(kind="palm", user_id=uid, payload={"leftHand": "x"})
    check("a UUID user_id enqueues (Postgres returns uuid.UUID)", True)
except TypeError as exc:
    check("a UUID user_id enqueues (Postgres returns uuid.UUID)", False, str(exc))
    job = None

if job:
    check("userId is stored as a string, not a UUID repr",
          job["userId"] == str(uid), f"got {job['userId']!r}")
    back = Q.load(job["jobId"])
    check("the job survives the round trip", bool(back), str(back))
    if back:
        check("the round trip preserves userId", back.get("userId") == str(uid))
        check("the round trip preserves the payload",
              (back.get("payload") or {}).get("leftHand") == "x")

print("\n— the other types a real driver hands back —")
CASES = {
    "datetime": datetime(2026, 8, 5, 1, 30, tzinfo=timezone.utc),
    "date": date(1985, 3, 8),
    "Decimal": Decimal("1499.00"),
    "UUID in payload": uuid.uuid4(),
}
for label, value in CASES.items():
    try:
        j = Q.enqueue(kind="chart_summary", user_id=str(uuid.uuid4()),
                      payload={"v": value})
        ok = bool(Q.load(j["jobId"]))
    except TypeError as exc:
        ok, detail = False, str(exc)
    else:
        detail = ""
    check(f"a {label} in the payload enqueues", ok, detail)

print("\n— the serialiser itself —")
check("_dumps exists and is used by enqueue", hasattr(Q, "_dumps"))
if hasattr(Q, "_dumps"):
    check("_dumps handles a UUID",
          json.loads(Q._dumps({"u": uuid.uuid4()}))["u"] is not None)
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "queue.py")).read()
# A bare json.dumps here is the bug coming back.
check("no bare json.dumps(job) left in queue.py",
      "json.dumps(job)" not in src,
      "a plain dumps will fail again the moment Postgres is in front of it")

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED: " + ", ".join(FAIL))
sys.exit(1 if FAIL else 0)
