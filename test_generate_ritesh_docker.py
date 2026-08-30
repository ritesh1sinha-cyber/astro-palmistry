#!/usr/bin/env python3
"""
test_generate_ritesh_docker.py — Generate Free and Paid Astro Reports for Ritesh via Docker API.
Tests both with LLM and without LLM.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

API_BASE = "http://localhost:8080"
OUTPUT_DIR = Path(r"C:\Users\rites\Downloads\apk_extracted\frontend\backend\reports\Ritesh_Docker_Reports")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RITESH_PAYLOAD = {
    "name": "Ritesh",
    "dob": "1985-03-08",
    "tob": "13:05",
    "place": "Patna, India",
    "lat": 25.5941,
    "lon": 85.1376,
    "tz": 5.5,
    "gender": "male",
}


def http_req(path: str, body: dict | None = None, token: str = "") -> dict | bytes:
    url = API_BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if body is not None else "GET")
    with urllib.request.urlopen(req, timeout=300) as resp:
        content_type = resp.headers.get("Content-Type", "")
        res_bytes = resp.read()
        if "application/json" in content_type:
            return json.loads(res_bytes.decode("utf-8"))
        return res_bytes


def run_docker_flow(test_label: str):
    print("=" * 65)
    print(f"RUNNING DOCKER REPORT GENERATION FOR RITESH ({test_label})")
    print("=" * 65)

    # 1. Auth dev user
    email = f"ritesh-test-{int(time.time())}@localdev.org"
    auth_res = http_req("/api/auth/dev", {"email": email, "name": "Ritesh", "passcode": "graharekha"})
    token = auth_res["token"]
    user_id = auth_res["user"]["id"]
    print(f" [1] Authenticated session for {email} (User ID: {user_id[:8]}...)")

    # 2. Submit full report job
    print(" [2] Submitting 'full_report' job to Docker API...")
    job = http_req("/api/job", {"kind": "full_report", "payload": RITESH_PAYLOAD}, token=token)
    job_id = job["jobId"]
    print(f"     Job ID: {job_id} | Status: {job.get('status')}")

    # 3. Poll for completion
    t0 = time.time()
    while job.get("status") in ("queued", "processing"):
        time.sleep(3)
        job = http_req(f"/api/job/{job_id}", token=token)
        elapsed = time.time() - t0
        print(f"     -> Waiting... ({elapsed:.1f}s) status={job.get('status')}", flush=True)
        if elapsed > 180:
            raise TimeoutError("Job took more than 180s")

    if job.get("status") != "done":
        raise RuntimeError(f"Job failed with: {job.get('error')}")

    res = job.get("result") or {}
    report_id = res.get("reportId")
    print(f" [3] Job Completed in {time.time() - t0:.1f}s! Report ID: {report_id}")

    # 4. Fetch Free Report
    rep_meta = http_req(f"/api/reports/{report_id}", token=token)
    free_url = rep_meta["links"]["free"]
    free_html = http_req(free_url, token=token).decode("utf-8")
    free_path = OUTPUT_DIR / f"Ritesh_Free_Astro_Report_{test_label}.html"
    free_path.write_text(free_html, encoding="utf-8")
    print(f" [4] Free HTML Report Saved: {free_path} ({len(free_html)} bytes)")

    # 5. Emulate payment & unlock Paid Report
    order = http_req("/api/order", {"item": "full_report", "refId": report_id}, token=token)
    order_id = order.get("orderId")
    print(f" [5] Created Order {order_id} (Amount: INR {order.get('amount')})")

    wh = http_req("/api/payment/webhook", {"orderId": order_id}, token=token)
    print(f"     Webhook granted access: {wh.get('ok')}")

    rep_paid = http_req(f"/api/reports/{report_id}", token=token)
    paid_url = rep_paid["links"]["paid"]
    paid_html = http_req(paid_url, token=token).decode("utf-8")
    paid_path = OUTPUT_DIR / f"Ritesh_Paid_Astro_Report_{test_label}.html"
    paid_path.write_text(paid_html, encoding="utf-8")
    print(f" [6] Paid HTML Report Saved: {paid_path} ({len(paid_html)} bytes)")

    return {
        "free_path": free_path,
        "paid_path": paid_path,
        "free_bytes": len(free_html),
        "paid_bytes": len(paid_html),
        "report_id": report_id,
        "meta": rep_meta.get("meta", {}),
    }


def run_no_llm_flow():
    print("\n" + "=" * 65)
    print("RUNNING DIRECT PYTHON REPORT GENERATION WITHOUT LLM")
    print("=" * 65)
    
    import sys
    sys.path.insert(0, "engines/astro")
    from astro_precompute import resolve_precompute
    import report_render as RD

    pc = resolve_precompute(
        "Ritesh", "1985-03-08", birth_time="13:05",
        latitude=25.5941, longitude=85.1376, timezone=5.5,
        place_name="Patna, India", gender=0
    )
    
    # Render with LLM disabled in renderer
    free_html, paid_html, meta = RD.full_report(
        pc, name="Ritesh", price=298, bundle_price=298,
        lat=25.5941, lon=85.1376, tz=5.5
    )

    free_path = OUTPUT_DIR / "Ritesh_Free_Astro_Report_No_LLM.html"
    paid_path = OUTPUT_DIR / "Ritesh_Paid_Astro_Report_No_LLM.html"

    free_path.write_text(free_html, encoding="utf-8")
    paid_path.write_text(paid_html, encoding="utf-8")

    print(f" [1] Free HTML (No-LLM) Saved: {free_path} ({len(free_html)} bytes)")
    print(f" [2] Paid HTML (No-LLM) Saved: {paid_path} ({len(paid_html)} bytes)")


if __name__ == "__main__":
    res_llm = run_docker_flow("LLM_Enabled")
    run_no_llm_flow()
    print("\n[SUCCESS] Both LLM and Non-LLM Free & Paid reports generated successfully!")
