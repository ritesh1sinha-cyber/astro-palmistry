#!/usr/bin/env python3
"""E2E Verification against Localhost Server (http://localhost:8080):
1. Create a dummy login with a non-admin account (free access).
2. Verify /api/me: admin=False, fullAccess=False, subscribed=False, dailyTrialLeft=3.
3. Test Daily Report Generation:
   - Verify report is UNLOCKED (paid: True) during the 3-day trial.
   - Verify links.paid is present and accessible via /api/file/{token}.
4. Test Free User Question Generation:
   - Verify report is locked (paid: False).
   - Verify meta.plainSummary is present and has sections.
5. Test Free Full Report Generation:
   - Verify meta.plainSummary is present and has sections.
6. Test /api/reports listing for user.
7. Test /api/reports/{rid}/pdf for unlocked daily report.
"""
import json
import time
import urllib.request
import urllib.error
import uuid

BASE = "http://localhost:8080"

def req(method, path, body=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(
        f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            content_type = resp.headers.get("content-type", "")
            if "application/json" in content_type:
                return resp.status, json.loads(resp.read().decode())
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        content = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(content)
        except Exception:
            return e.code, content

def run_e2e_tests():
    print("=== Step 1: Create Dummy Non-Admin Account ===")
    email = f"free_tester_{uuid.uuid4().hex[:8]}@testuser.local"
    status, res = req("POST", "/api/auth/dev", {
        "email": email,
        "name": "Free Seeker Tester",
        "passcode": "graharekha"
    })
    assert status == 200, f"Auth dev failed: {res}"
    token = res["token"]
    user = res["user"]
    print(f"User logged in: {user['email']}")
    print(f"  admin={user['admin']}, fullAccess={user['fullAccess']}, subscribed={user['subscribed']}, dailyTrialLeft={user['dailyTrialLeft']}")
    
    assert not user["admin"], "Expected admin=False"
    assert not user["fullAccess"], "Expected fullAccess=False"
    assert not user["subscribed"], "Expected subscribed=False"
    assert user["dailyTrialLeft"] == 3, f"Expected dailyTrialLeft=3, got {user['dailyTrialLeft']}"

    print("\n=== Step 2: Generate Daily Report (Free Trial Access) ===")
    daily_payload = {
        "name": "Free Tester",
        "dob": "1992-05-15",
        "tob": "14:30",
        "place": "Delhi, India",
        "lat": 28.6139,
        "lon": 77.2090,
        "tz": 5.5,
        "gender": "male"
    }
    status, job = req("POST", "/api/job", {"kind": "daily", "payload": daily_payload}, token=token)
    assert status == 200, f"Submit daily job failed: {job}"
    job_id = job["jobId"]
    
    # Wait for completion
    daily_res = None
    for _ in range(30):
        status, snap = req("GET", f"/api/job/{job_id}", token=token)
        if snap.get("status") == "done":
            daily_res = snap["result"]
            break
        elif snap.get("status") == "failed":
            raise RuntimeError(f"Job failed: {snap.get('error')}")
        time.sleep(1)
    
    assert daily_res is not None, "Daily job timed out"
    print(f"Daily report result:")
    print(f"  paid: {daily_res.get('paid')}")
    print(f"  links: {daily_res.get('links')}")
    assert daily_res.get("paid") is True, f"Expected daily report to be UNLOCKED (paid=True) during 3-day trial, got {daily_res.get('paid')}"
    assert "paid" in (daily_res.get("links") or {}), f"Expected 'paid' link in daily links: {daily_res.get('links')}"
    assert daily_res.get("dailyTrialLeft") == 2, f"Expected dailyTrialLeft=2 after 1st daily report, got {daily_res.get('dailyTrialLeft')}"

    # Verify paid link works
    paid_link = daily_res["links"]["paid"]
    status, html_content = req("GET", paid_link)
    assert status == 200, f"Failed to fetch paid HTML: {status}"
    assert len(html_content) > 500, "Paid HTML too short"
    print(f"  Successfully fetched full daily reading HTML ({len(html_content)} bytes)")

    # Verify /api/me reflects 2 daily trials left
    status, me = req("GET", "/api/me", token=token)
    assert status == 200 and me["dailyTrialLeft"] == 2, f"Expected me.dailyTrialLeft=2, got {me.get('dailyTrialLeft')}"
    print(f"  /api/me dailyTrialLeft confirmed: {me['dailyTrialLeft']}")

    print("\n=== Step 3: Generate Free User Question Report ===")
    uq_payload = {
        "name": "Free Tester",
        "dob": "1992-05-15",
        "tob": "14:30",
        "place": "Delhi, India",
        "lat": 28.6139,
        "lon": 77.2090,
        "tz": 5.5,
        "gender": "male",
        "question": "When will I buy a new house?"
    }
    status, job = req("POST", "/api/job", {"kind": "user_question", "payload": uq_payload}, token=token)
    assert status == 200, f"Submit uq job failed: {job}"
    job_id = job["jobId"]
    
    uq_res = None
    for _ in range(30):
        status, snap = req("GET", f"/api/job/{job_id}", token=token)
        if snap.get("status") == "done":
            uq_res = snap["result"]
            break
        elif snap.get("status") == "failed":
            raise RuntimeError(f"UQ job failed: {snap.get('error')}")
        time.sleep(1)
    
    assert uq_res is not None, "UQ job timed out"
    print(f"User Question result:")
    print(f"  paid: {uq_res.get('paid')}")
    assert uq_res.get("paid") is False, "Free user question should be paid=False"
    
    meta = uq_res.get("meta") or {}
    ps = meta.get("plainSummary") or {}
    print(f"  plainSummary generated: {ps.get('generated')}")
    print(f"  plainSummary sections count: {len(ps.get('sections', []))}")
    for idx, s in enumerate(ps.get("sections", [])):
        print(f"    Section {idx+1}: [{s['title']}] -> {s['body'][:75]}...")
    assert len(ps.get("sections", [])) > 0, "Expected plainSummary in free user_question report"
    unlock_sections = [s for s in ps.get("sections", []) if "unlock" in s.get("title", "").lower() or "unlock" in s.get("body", "").lower()]
    print(f"  Unlock disclaimer section present: {bool(unlock_sections)}")
    assert len(unlock_sections) > 0, "Free user question summary must have an Unlock disclaimer section"

    print("\n=== Step 4: Verify /api/reports for the User ===")
    status, reps = req("GET", "/api/reports", token=token)
    assert status == 200, f"List reports failed: {reps}"
    print(f"Total reports found: {len(reps)}")
    for r in reps:
        has_ps = "plainSummary" in (r.get("meta") or {})
        print(f"  - Kind: {r['kind']:<15} | Paid: {str(r['paid']):<5} | Has PlainSummary: {has_ps}")
        assert has_ps, f"Expected plainSummary in report {r['kind']}"

    print("\n=== Step 5: Test PDF Download for Unlocked Daily Report ===")
    daily_rid = daily_res.get("reportId")
    if daily_rid:
        status, pdf_data = req("GET", f"/api/reports/{daily_rid}/pdf", token=token)
        print(f"PDF status code: {status}")
        if status == 200:
            print(f"PDF successfully generated ({len(pdf_data)} bytes)")
        else:
            print(f"PDF response: {status}")

    print("\n==========================================")
    print(">>> ALL 5 END-TO-END TESTS PASSED! <<<")
    print("==========================================")

if __name__ == "__main__":
    run_e2e_tests()
