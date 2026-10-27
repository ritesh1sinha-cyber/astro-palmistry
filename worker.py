#!/usr/bin/env python3
"""
worker.py — pulls jobs from Redis and runs the engines.

One job at a time per process (the engines are CPU-bound), so total concurrency
is simply the number of worker replicas, capped per-kind by the Redis slot
budget in core.queue. Scale by adding replicas.

    WORKER_GROUPS=heavy,palm,light python worker.py

Groups let you dedicate machines: put `heavy` (full reports, birth-time
rectification) on a big box and `light` (chart summaries, horary, daily) on a
small one, so a 3-minute report never delays a 2-second answer.
"""

from __future__ import annotations

import os
import signal
import socket
import sys
import time
import traceback
import uuid

from core import queue as Q
from core.config import S
from core.db import init_schema, job_update, now

WORKER_ID = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:4]}"
GROUPS = [g.strip() for g in os.getenv("WORKER_GROUPS", "heavy,palm,light").split(",") if g.strip()]
IDLE_SLEEP = float(os.getenv("WORKER_IDLE_SLEEP", "0.5"))
MAX_ATTEMPTS = int(os.getenv("WORKER_MAX_ATTEMPTS", "2"))

_stop = False


def _graceful(signum, frame):            # noqa: ARG001
    global _stop
    _stop = True
    print(f"[worker {WORKER_ID}] signal {signum} — finishing current job then exiting",
          flush=True)


signal.signal(signal.SIGTERM, _graceful)
signal.signal(signal.SIGINT, _graceful)


from core.errors import UserError


def friendly(exc: Exception) -> str:
    msg = str(exc)
    low = msg.lower()
    if "landmark" in low or "palm" in low and "unread" in low:
        return ("We could not find a clear palm in one of the photos. Retake in "
                "bright light with the hand flat, open and filling the frame.")
    if "both palms" in low:
        return "Both palms are needed for a reading."
    if "hand_landmarker" in low or "mediapipe" in low:
        return "The image analyser is unavailable right now. Please try again shortly."
    # Only messages someone wrote FOR a reader are shown. The old rule passed
    # through any short ValueError, which put "invalid literal for int() with
    # base 10: 'male'" in front of a paying customer.
    if isinstance(exc, UserError):
        return msg
    return "We could not complete this reading. Please try again."


def run_once() -> bool:
    from core.db import engine
    from core.handlers import HANDLERS
    from sqlalchemy import text

    for group in GROUPS:
        job = Q.claim(group, WORKER_ID)
        if not job:
            continue

        pid, kind = job["jobId"], job["kind"]
        job_update(pid, status="processing", started_at=now(), worker_id=WORKER_ID)
        t0 = time.time()
        print(f"[worker] {pid} {kind} start", flush=True)

        try:
            with engine().connect() as c:
                row = c.execute(text("SELECT * FROM users WHERE id = :u"),
                                {"u": job["userId"]}).fetchone()
            user = dict(row._mapping) if row else {"id": job["userId"], "name": "Seeker"}

            result = HANDLERS[kind](user, job.get("payload") or {})
            Q.finish(job, result=result)
            job_update(pid, status="done", finished_at=now(),
                       duration_ms=int((time.time() - t0) * 1000),
                       report_id=result.get("reportId") if isinstance(result, dict) else None)
            print(f"[worker] {pid} {kind} done in {time.time() - t0:.1f}s", flush=True)

        except Exception as exc:                                      # noqa: BLE001
            traceback.print_exc()
            attempts = int(job.get("attempts", 0)) + 1
            job["attempts"] = attempts
            transient = isinstance(exc, (ConnectionError, TimeoutError, OSError))
            if transient and attempts < MAX_ATTEMPTS:
                # release the slot and put it back at the front of its band
                Q.release_slot(kind, f"{WORKER_ID}:{pid}")
                job["status"] = "queued"
                Q.save(job)
                Q.r().zadd(Q._q(Q.group_of(kind)),
                           {pid: job.get("priority", 5) * 1e12 + time.time() - 1e6})
                job_update(pid, status="queued", attempts=attempts)
                print(f"[worker] {pid} retry {attempts}", flush=True)
            else:
                Q.finish(job, error=friendly(exc))
                try:
                    from core.billing import refund_report_generation
                    refund_report_generation(job["userId"], kind)
                except Exception:                                     # noqa: BLE001
                    pass
                job_update(pid, status="failed", finished_at=now(),
                           attempts=attempts, error=str(exc)[:900],
                           duration_ms=int((time.time() - t0) * 1000))
        return True
    return False


def main() -> None:
    init_schema()
    print(f"[worker {WORKER_ID}] groups={GROUPS} caps={S.kind_caps}", flush=True)
    idle = 0
    while not _stop:
        try:
            did = run_once()
        except Exception:                                             # noqa: BLE001
            traceback.print_exc()
            time.sleep(2)
            continue
        if did:
            idle = 0
        else:
            idle += 1
            # back off gently when there is nothing to do, so an idle fleet is cheap
            time.sleep(min(IDLE_SLEEP * (1 + idle // 20), 3.0))
    print(f"[worker {WORKER_ID}] stopped", flush=True)


if __name__ == "__main__":
    sys.exit(main())
