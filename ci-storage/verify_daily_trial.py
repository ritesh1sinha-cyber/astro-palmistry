#!/usr/bin/env python3
"""Verify 3-day full daily trial, then lock until subscription."""
import json
import sys
import time
import urllib.request

BASE = "http://localhost:8080"
SAMPLE = {
    "name": "Trial User",
    "dob": "1985-06-20",
    "tob": "09:30",
    "place": "Mumbai, India",
    "lat": 19.076,
    "lon": 72.8777,
    "tz": 5.5,
    "gender": "female",
}


def req(method, path, body=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(
        f"{BASE}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=120) as resp:
        return json.loads(resp.read().decode())


def daily(token):
    job = req("POST", "/api/job", {"kind": "daily", "payload": SAMPLE}, token=token)
    pid = job["jobId"]
    for _ in range(60):
        snap = req("GET", f"/api/job/{pid}", token=token)
        if snap["status"] == "done":
            return snap["result"]
        if snap["status"] == "failed":
            raise RuntimeError(snap.get("error"))
        time.sleep(2)
    raise TimeoutError("daily timed out")


def main() -> int:
    email = f"trial-{int(time.time())}@guest.local"
    tok = req("POST", "/api/auth/dev", {
        "name": "Trial", "email": email, "passcode": "graharekha",
    })["token"]
    me = req("GET", "/api/me", token=tok)
    print(f"start dailyTrialLeft={me.get('dailyTrialLeft')}")
    ok = True
    for i in range(1, 5):
        r = daily(tok)
        paid = bool(r.get("paid"))
        left = r.get("dailyTrialLeft")
        has_paid = "paid" in (r.get("links") or {})
        print(f"  run {i}: paid={paid} trialLeft={left} paidLink={has_paid}")
        expect_paid = i <= 3
        if paid != expect_paid:
            print(f"FAIL run {i}: expected paid={expect_paid}")
            ok = False
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
