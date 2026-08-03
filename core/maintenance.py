#!/usr/bin/env python3
"""
Nightly housekeeping. Runs as its own container (`cron` in compose).

    python -m core.maintenance --once     # one pass
    python -m core.maintenance --loop     # sleep until 03:15 IST, repeat

What it does, and why each one matters at 1 lakh users:

  * roll monthly partitions forward — a missing partition means INSERTs start
    failing at midnight on the 1st, so this runs every night, not monthly.
  * prune expired reports (DB rows AND the objects) — 1M reports × ~200 KB is
    200 GB of storage nobody is reading.
  * prune old job rows — history is useful for 90 days, not forever.
  * evict cold precomputes — the cache is only worth its disk while it is warm.
  * expire subscriptions whose period has ended, and revoke what they granted.
  * back up Postgres and verify the dump is non-trivial.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from .config import S
from .db import engine, extend_partitions, now, tx
from .store import store


def prune_reports() -> int:
    """Delete expired reports and their objects. Objects first: an orphaned row
    is recoverable, an orphaned object is invisible and costs money forever."""
    with engine().connect() as c:
        rows = c.execute(text(
            "SELECT id, free_key, paid_key FROM reports"
            " WHERE expires_at IS NOT NULL AND expires_at < :now LIMIT 5000"),
            {"now": now()}).fetchall()
    st = store()
    ids = []
    for r in rows:
        m = r._mapping
        for k in (m["free_key"], m["paid_key"]):
            if k:
                try:
                    st.delete(k)
                except Exception as exc:                              # noqa: BLE001
                    print(f"  ! could not delete {k}: {exc}", flush=True)
        ids.append(m["id"])
    if ids:
        with tx() as c:
            if S.is_postgres:
                c.execute(text("DELETE FROM reports WHERE id = ANY(:ids)"), {"ids": ids})
            else:
                # SQLite has no array binding; parameterised IN list instead of
                # string interpolation (never build SQL out of values)
                marks = ",".join(f":i{n}" for n in range(len(ids)))
                c.execute(text(f"DELETE FROM reports WHERE id IN ({marks})"),
                          {f"i{n}": v for n, v in enumerate(ids)})
    return len(ids)


def prune_jobs() -> int:
    cutoff = now() - timedelta(days=S.job_retention_days)
    with tx() as c:
        res = c.execute(text("DELETE FROM jobs WHERE created_at < :c"), {"c": cutoff})
    return res.rowcount or 0


def evict_cold_precomputes(days: int = 120) -> int:
    """Drop cache entries nobody has touched. They regenerate on demand."""
    cutoff = now() - timedelta(days=days)
    with engine().connect() as c:
        rows = c.execute(text("SELECT chart_hash, engine_version, payload_key"
                              " FROM precomputes WHERE last_used_at < :c LIMIT 5000"),
                         {"c": cutoff}).fetchall()
    st = store()
    n = 0
    for r in rows:
        m = r._mapping
        if m["payload_key"]:
            try:
                st.delete(m["payload_key"])
            except Exception:                                         # noqa: BLE001
                pass
        with tx() as c:
            c.execute(text("DELETE FROM precomputes WHERE chart_hash=:h"
                           " AND engine_version=:v"),
                      {"h": m["chart_hash"], "v": m["engine_version"]})
        n += 1
    return n


def expire_subscriptions() -> int:
    with tx() as c:
        res = c.execute(text(
            "UPDATE subscriptions SET status = 'expired'"
            " WHERE status = 'active' AND current_period_end < :now"),
            {"now": now()})
        # and revoke what those subscriptions were granting
        c.execute(text(
            "UPDATE entitlements SET revoked_at = :now"
            " WHERE source = 'subscription' AND revoked_at IS NULL"
            "   AND expires_at IS NOT NULL AND expires_at < :now"),
            {"now": now()})
    return res.rowcount or 0


def backup_postgres(out_dir: str = "/backups") -> str:
    if not S.is_postgres:
        return "skipped (not postgres)"
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    path = os.path.join(out_dir, f"astro-{stamp}.dump")
    url = S.database_url.replace("postgresql+psycopg://", "postgresql://")
    try:
        subprocess.run(["pg_dump", "--format=custom", "--file", path, url],
                       check=True, timeout=1800)
    except FileNotFoundError:
        return "pg_dump not installed in this image"
    except subprocess.CalledProcessError as exc:
        return f"FAILED: {exc}"
    size = os.path.getsize(path)
    if size < 10_000:
        return f"SUSPECT: dump is only {size} bytes — check credentials"
    # keep 14 days
    for f in sorted(os.listdir(out_dir)):
        p = os.path.join(out_dir, f)
        if f.startswith("astro-") and time.time() - os.path.getmtime(p) > 14 * 86400:
            os.remove(p)
    return f"{path} ({size / 1e6:.1f} MB)"


def one_pass() -> None:
    print(f"[maintenance] start {now().isoformat()}", flush=True)
    extend_partitions()
    print(f"  partitions rolled", flush=True)
    print(f"  reports pruned: {prune_reports()}", flush=True)
    print(f"  jobs pruned: {prune_jobs()}", flush=True)
    print(f"  cold precomputes evicted: {evict_cold_precomputes()}", flush=True)
    print(f"  subscriptions expired: {expire_subscriptions()}", flush=True)
    print(f"  backup: {backup_postgres()}", flush=True)
    print("[maintenance] done", flush=True)


def seconds_until(hour_ist: int = 3, minute: int = 15) -> float:
    ist = timezone(timedelta(hours=5, minutes=30))
    nowi = datetime.now(ist)
    target = nowi.replace(hour=hour_ist, minute=minute, second=0, microsecond=0)
    if target <= nowi:
        target += timedelta(days=1)
    return (target - nowi).total_seconds()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--loop", action="store_true")
    a = ap.parse_args()
    if a.once or not a.loop:
        one_pass()
        return 0
    while True:
        wait = seconds_until()
        print(f"[maintenance] sleeping {wait / 3600:.1f}h", flush=True)
        time.sleep(wait)
        try:
            one_pass()
        except Exception as exc:                                      # noqa: BLE001
            print(f"[maintenance] pass failed: {exc}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
