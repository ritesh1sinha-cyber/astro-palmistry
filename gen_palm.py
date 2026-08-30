import base64
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

API_BASE = 'http://localhost:8080'
OUTPUT_DIR = Path(r'C:\Users\rites\Downloads\apk_extracted\frontend\backend\reports\Ritesh_Docker_Reports')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LEFT_PALM = Path(r'c:\Users\rites\Downloads\apk_extracted\frontend\backend\_astro_sessions\6c08d135-359a-4fd2-89ec-53ed7c49c3dd\input\ritz_leftpalm.jpg')
RIGHT_PALM = Path(r'c:\Users\rites\Downloads\apk_extracted\frontend\backend\_astro_sessions\6c08d135-359a-4fd2-89ec-53ed7c49c3dd\input\ritz_rightpalm.jpg')

def http_req(path: str, body: dict | None = None, token: str = '') -> dict | bytes:
    url = API_BASE + path
    data = json.dumps(body).encode('utf-8') if body is not None else None
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(url, data=data, headers=headers, method='POST' if body is not None else 'GET')
    with urllib.request.urlopen(req, timeout=300) as resp:
        content_type = resp.headers.get('Content-Type', '')
        res_bytes = resp.read()
        if 'application/json' in content_type:
            return json.loads(res_bytes.decode('utf-8'))
        return res_bytes

def main():
    print('=' * 65)
    print('RUNNING DOCKER PALM REPORT GENERATION FOR RITZ')
    print('=' * 65)

    email = f'ritz-palm-{int(time.time())}@localdev.org'
    auth_res = http_req('/api/auth/dev', {'email': email, 'name': 'Ritz', 'passcode': 'graharekha'})
    token = auth_res['token']
    user_id = auth_res['user']['id']
    print(f' [1] Authenticated session for {email} (User ID: {user_id[:8]}...)')

    left_b64 = 'data:image/jpeg;base64,' + base64.b64encode(LEFT_PALM.read_bytes()).decode('utf-8')
    right_b64 = 'data:image/jpeg;base64,' + base64.b64encode(RIGHT_PALM.read_bytes()).decode('utf-8')

    palm_payload = {
        'name': 'Ritz',
        'age': 41,
        'gender': 'male',
        'dominant': 'right',
        'leftHand': left_b64,
        'rightHand': right_b64,
        'language': 'en'
    }

    print(' [2] Submitting palm job to Docker API...')
    job_res = http_req('/api/job', {'kind': 'palm', 'payload': palm_payload}, token=token)
    job_id = job_res['jobId']
    print(f"     Job ID: {job_id} | Status: {job_res.get('status')}")

    start_time = time.time()
    while True:
        time.sleep(3.0)
        elapsed = time.time() - start_time
        poll_res = http_req(f"/api/job/{job_id}", token=token)
        st = poll_res.get("status")
        print(f"     -> Waiting... ({elapsed:.1f}s) status={st}")
        if st == "done":
            res = poll_res.get("result", {})
            break
        elif st == "failed":
            raise RuntimeError(f"Job failed: {poll_res.get('error')}")

    duration = time.time() - start_time
    report_id = res["reportId"]
    print(f" [3] Job Completed in {duration:.1f}s! Report ID: {report_id}")

    # Free HTML
    rep_meta = http_req(f"/api/reports/{report_id}", token=token)
    free_url = rep_meta["links"]["free"]
    free_html = http_req(free_url, token=token).decode("utf-8")
    free_path = OUTPUT_DIR / "Ritz_Free_Palm_Report.html"
    free_path.write_text(free_html, encoding="utf-8")
    print(f" [4] Free HTML Report Saved: {free_path} ({len(free_html)} bytes)")

    # Unlock Paid View
    order = http_req("/api/order", {"item": "palm_full", "refId": report_id}, token=token)
    order_id = order.get("orderId")
    print(f" [5] Created Order {order_id} (Amount: INR {order.get('amount')})")

    wh = http_req("/api/payment/webhook", {"orderId": order_id}, token=token)
    print(f"     Webhook granted access: {wh.get('ok')}")

    # Paid HTML
    rep_paid = http_req(f"/api/reports/{report_id}", token=token)
    paid_url = rep_paid["links"]["paid"]
    paid_html = http_req(paid_url, token=token).decode("utf-8")
    paid_path = OUTPUT_DIR / "Ritz_Paid_Palm_Report.html"
    paid_path.write_text(paid_html, encoding="utf-8")
    print(f" [6] Paid HTML Report Saved: {paid_path} ({len(paid_html)} bytes)")

    print("\n[SUCCESS] Ritz's Free and Paid Palmistry Reports successfully generated and verified!")

if __name__ == '__main__':
 main()
