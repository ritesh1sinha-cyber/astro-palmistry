import base64
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

BASE_URL = http://localhost:8080
OUT_DIR = Path(rC:\Users\rites\Downloads\apk_extracted\frontend\backend\reports\Ritesh_Docker_Reports)
OUT_DIR.mkdir(parents=True, exist_ok=True)

LEFT_PALM = Path(rc:\Users\rites\Downloads\apk_extracted\frontend\backend\_astro_sessions\6c08d135-359a-4fd2-89ec-53ed7c49c3dd\input\ritz_leftpalm.jpg)
RIGHT_PALM = Path(rc:\Users\rites\Downloads\apk_extracted\frontend\backend\_astro_sessions\6c08d135-359a-4fd2-89ec-53ed7c49c3dd\input\ritz_rightpalm.jpg)


def http_req(endpoint: str, data: dict | None = None, token: str | None = None) -> dict:
    url = f{BASE_URL}{endpoint}
    headers = {Content-Type: application/json}
    if token:
        headers[Authorization] = fBearer {token}
    body = json.dumps(data).encode(utf-8) if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=POST if data is not None else GET)
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode(utf-8))


def run_palm_docker_test():
    print(= * 65)
    print(RUNNING DOCKER PALMISTRY REPORT GENERATION FOR RITZ)
    print(= * 65)

    # 1. Dev Auth
    email = fritz-palm-{int(time.time())}@localdev.org
    auth_res = http_req(/api/auth/dev, {email: email, name: Ritz, passcode: graharekha})
    token = auth_res.get(token) or (auth_res.get(user) or {}).get(token)
    user_id = (auth_res.get(user) or {}).get(id)
    print(f [1] Authenticated session for {email} (User ID: {user_id[:8]}...))

    # 2. Encode Palms
    left_b64 = data:image/jpeg;base64, + base64.b64encode(LEFT_PALM.read_bytes()).decode(utf-8)
    right_b64 = data:image/jpeg;base64, + base64.b64encode(RIGHT_PALM.read_bytes()).decode(utf-8)

    # 3. Submit Palm Job
    palm_payload = {
        name: Ritz,
        age: 41,
        gender: male,
        dominant: right,
        leftHand: left_b64,
        rightHand: right_b64,
        language: en
    }

    print( [2] Submitting 'palm' job to Docker API...)
    job_res = http_req(/api/job/palm, palm_payload, token=token)
    job_id = job_res.get(jobId)
    status = job_res.get(status)
    print(f Job ID: {job_id} | Status: {status})

    # 4. Poll
    start_time = time.time()
    while status in (queued, processing):
        time.sleep(3.0)
        elapsed = time.time() - start_time
        poll_res = http_req(f/api/job/{job_id}, token=token)
        status = poll_res.get(status)
        print(f -> Waiting... ({elapsed:.1f}s) status={status})
        if status == done:
            result = poll_res.get(result, {})
            break
        elif status == failed:
            raise RuntimeError(fJob failed: {poll_res.get('error')})

    duration = time.time() - start_time
    report_id = result.get(reportId)
    print(f [3] Job Completed in {duration:.1f}s! Report ID: {report_id})

    # 5. Fetch Free HTML Report
    free_res = http_req(f/api/report/{report_id}?view=free, token=token)
    free_html = free_res.get(html, ")
 free_path = OUT_DIR / Ritz_Free_Palm_Report.html
 free_path.write_text(free_html, encoding=utf-8)
 print(f [4] Free Palm HTML Saved: {free_path} ({len(free_html)} bytes))

 # 6. Create Order and Unlock Paid View
 order_res = http_req(/api/payment/create, {reportId: report_id, kind: palm_full}, token=token)
 order_id = order_res.get(orderId)
 http_req(/api/payment/dev_bypass, {orderId: order_id}, token=token)
 print(f [5] Created & Bypassed Order {order_id} (Paid Unlocked))

 # 7. Fetch Paid HTML Report
 paid_res = http_req(f/api/report/{report_id}?view=paid, token=token)
 paid_html = paid_res.get(html, )
 paid_path = OUT_DIR / Ritz_Paid_Palm_Report.html
 paid_path.write_text(paid_html, encoding=utf-8)
 print(f [6] Paid Palm HTML Saved: {paid_path} ({len(paid_html)} bytes))

 print(\n[SUCCESS] Ritz's Free & Paid Palmistry Reports Generated Successfully via Docker!)


if __name__ == __main__:
 run_palm_docker_test()
