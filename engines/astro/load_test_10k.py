"""
Load test: 10,000 POST /v1/jobs submissions (burst / high concurrency).

Uses threaded waves — reliable on Windows (async 10k connections often hangs).

  set DISABLE_RATE_LIMIT=true on API
  python load_test_10k.py --base http://127.0.0.1:8000
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

import requests

DEFAULT_BASE = "http://127.0.0.1:8000"
USERNAME = "demo"
PASSWORD = "demo123"


@dataclass
class LoadResult:
    total: int = 0
    accepted: int = 0
    rate_limited: int = 0
    busy: int = 0
    errors: int = 0
    latencies_ms: list[float] = field(default_factory=list)
    status_counts: dict[int, int] = field(default_factory=dict)
    elapsed_s: float = 0.0


def login(base: str, session: requests.Session) -> str:
    r = session.post(
        f"{base}/auth/login",
        json={"username": USERNAME, "password": PASSWORD},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def submit_one(
    base: str,
    token: str,
    idx: int,
    session: requests.Session,
) -> tuple[int, float, str | None]:
    t0 = time.perf_counter()
    try:
        r = session.post(
            f"{base}/v1/jobs",
            json={"input": f"load-{idx}"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=60,
        )
        ms = (time.perf_counter() - t0) * 1000
        status = "accepted" if r.status_code in (200, 202) and r.json().get("status") in (
            "queued",
            "completed",
        ) else str(r.status_code)
        return r.status_code, ms, status
    except Exception:
        return 0, (time.perf_counter() - t0) * 1000, "error"


def run_load(base: str, count: int, wave_size: int) -> LoadResult:
    result = LoadResult(total=count)
    session = requests.Session()

    h = session.get(f"{base}/health", timeout=30).json()
    print(
        f"Pre-test: mode={h.get('mode')} redis={h.get('redis')} queue={h.get('queue_depth')}",
        flush=True,
    )

    token = login(base, session)
    print(f"Login OK — {count} jobs in waves of {wave_size} ...", flush=True)

    t0 = time.perf_counter()
    waves = (count + wave_size - 1) // wave_size

    for wave in range(waves):
        start = wave * wave_size
        end = min(start + wave_size, count)
        indices = range(start, end)
        with ThreadPoolExecutor(max_workers=wave_size) as pool:
            futures = [pool.submit(submit_one, base, token, i, session) for i in indices]
            for fut in as_completed(futures):
                code, ms, status = fut.result()
                result.latencies_ms.append(ms)
                if code:
                    result.status_counts[code] = result.status_counts.get(code, 0) + 1
                if status == "accepted":
                    result.accepted += 1
                elif code == 429:
                    result.rate_limited += 1
                elif code == 503:
                    result.busy += 1
                else:
                    result.errors += 1
        print(f"  wave {wave + 1}/{waves} done ({end}/{count})", flush=True)

    result.elapsed_s = time.perf_counter() - t0
    post = session.get(f"{base}/health", timeout=30).json()
    print(f"Post-test queue_depth={post.get('queue_depth')}", flush=True)
    return result


def print_report(result: LoadResult) -> int:
    elapsed = result.elapsed_s
    print("\n" + "=" * 56, flush=True)
    print("  10K LOAD TEST RESULTS", flush=True)
    print("=" * 56, flush=True)
    print(f"  Total requests:     {result.total}", flush=True)
    print(f"  Accepted (queued):  {result.accepted}", flush=True)
    print(f"  Rate limited (429): {result.rate_limited}", flush=True)
    print(f"  System busy (503):  {result.busy}", flush=True)
    print(f"  Other errors:       {result.errors}", flush=True)
    print(f"  Wall time:          {elapsed:.2f}s", flush=True)
    if elapsed > 0:
        print(f"  Submissions/sec:    {result.total / elapsed:.0f}", flush=True)
    print(f"  HTTP codes:         {dict(sorted(result.status_counts.items()))}", flush=True)

    if result.latencies_ms:
        ls = sorted(result.latencies_ms)
        print(f"  Latency p50:        {statistics.median(ls):.0f} ms", flush=True)
        print(f"  Latency p95:        {ls[int(len(ls) * 0.95)]:.0f} ms", flush=True)
        print(f"  Latency max:        {max(ls):.0f} ms", flush=True)
    print("=" * 56, flush=True)

    rate = result.accepted / result.total if result.total else 0
    if rate >= 0.95 and result.rate_limited == 0:
        print("  PASS: >=95% jobs accepted into queue", flush=True)
        return 0
    if result.rate_limited:
        print("  WARN: Set DISABLE_RATE_LIMIT=true on API for burst test", flush=True)
    print(f"  FAIL: {rate * 100:.1f}% accepted", flush=True)
    return 1


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base", default=DEFAULT_BASE)
    p.add_argument("--count", type=int, default=10_000)
    p.add_argument("--wave-size", type=int, default=500, help="Concurrent requests per wave")
    args = p.parse_args()
    print(f"Target: {args.base} | jobs={args.count} | wave={args.wave_size}\n", flush=True)
    try:
        return print_report(run_load(args.base, args.count, args.wave_size))
    except requests.RequestException as exc:
        print(f"FAIL: {exc}", flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
