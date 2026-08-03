"""End-to-end test for queue mode: health, login, HTML job report, concurrent batch."""
from __future__ import annotations

import concurrent.futures
import re
import sys
import time

import requests

from app.processor import content_type_for, generate_html_report, is_html_output

BASE = "http://127.0.0.1:8000"
TIMEOUT = 15


def login() -> str:
    r = requests.post(
        f"{BASE}/auth/login",
        json={"username": "demo", "password": "demo123"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def poll_job(token: str, job_id: str, max_wait: float = 20.0) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    deadline = time.time() + max_wait
    while time.time() < deadline:
        r = requests.get(f"{BASE}/v1/jobs/{job_id}", headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        if data["status"] in {"completed", "failed"}:
            return data
        time.sleep(0.2)
    raise TimeoutError(f"Job {job_id} not finished in {max_wait}s")


def submit_and_wait(token: str, text: str) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post(
        f"{BASE}/v1/jobs",
        json={"input": text},
        headers=headers,
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    created = r.json()
    if created.get("status") == "completed" and created.get("output"):
        return created
    result = poll_job(token, created["job_id"])
    if result["status"] != "completed":
        raise RuntimeError(result.get("error") or result)
    return result


def assert_html_report(payload: dict, label: str) -> None:
    output = payload.get("output", "")
    ctype = payload.get("output_content_type", content_type_for(output))
    if not is_html_output(output):
        raise AssertionError(f"{label}: output is not HTML")
    if ctype != "text/html":
        raise AssertionError(f"{label}: expected output_content_type=text/html, got {ctype!r}")
    if "Python Analysis Report" not in output:
        raise AssertionError(f"{label}: missing report title")
    if "<div class=\"chart\">" not in output:
        raise AssertionError(f"{label}: missing chart section")
    words = len(re.sub(r"<[^>]+>", " ", output).split())
    if words < 90:
        raise AssertionError(f"{label}: report too short ({words} words)")


def test_processor_local() -> None:
    html = generate_html_report("hi")
    assert is_html_output(html)
    assert content_type_for(html) == "text/html"
    words = len(re.sub(r"<[^>]+>", " ", html).split())
    assert words >= 90, f"processor report only {words} words"
    print(f"0. Processor local: HTML report OK ({words} words)")


def main() -> int:
    print("=== Python Bridge HTML report test ===\n")
    test_processor_local()

    h = requests.get(f"{BASE}/health", timeout=TIMEOUT).json()
    print("1. Health:", h)

    token = login()
    print("2. Login: OK")

    result = submit_and_wait(token, "hi")
    assert_html_report(result, "single job")
    print("3. Single job hi -> HTML report OK")
    print(f"   content_type={result.get('output_content_type')}")

    n = 20
    t0 = time.time()

    def one(_: int) -> dict:
        return submit_and_wait(token, "hi")

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(one, range(n)))
    elapsed = time.time() - t0
    ok = sum(1 for r in results if is_html_output(r.get("output", "")))
    print(f"4. Concurrent {n} HTML jobs: {ok}/{n} in {elapsed:.2f}s")
    if ok != n:
        print("   FAIL: not all jobs returned HTML")
        return 1

    # Built-in web UI static files
    root = requests.get(f"{BASE}/", timeout=TIMEOUT)
    if root.status_code != 200 or "Python Bridge" not in root.text:
        print("5. Web UI: FAIL (restart API to load / web files)")
        return 1
    print("5. Web UI: OK (open / in browser to see rendered report)")

    print("\n=== ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except requests.RequestException as exc:
        print(f"\nFAIL: API not reachable — {exc}")
        sys.exit(1)
