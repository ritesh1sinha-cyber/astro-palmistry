#!/usr/bin/env python3
"""Verify horary free/paid split after paywall redesign."""
import json
import sys
import time
import urllib.request

BASE = "http://localhost:8080"


def req(method, path, body=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=120) as resp:
        return json.loads(resp.read().decode())


def login(name="Guest"):
    return req("POST", "/api/auth/dev", {
        "name": name, "email": f"{name.lower()}@guest.local",
        "passcode": "graharekha",
    })["token"]


def submit_horary(token):
    job = req("POST", "/api/job", {
        "kind": "horary",
        "payload": {
            "question": "Will I get the promotion this year?",
            "qDate": "2026-08-07",
            "qTime": "15:00",
            "location": "New Delhi, India",
            "kpNumber": "108",
        },
    }, token=token)
    pid = job["jobId"]
    for _ in range(90):
        snap = req("GET", f"/api/job/{pid}", token=token)
        if snap["status"] == "done":
            return snap["result"]
        if snap["status"] == "failed":
            raise RuntimeError(snap.get("error") or "job failed")
        time.sleep(2)
    raise TimeoutError("horary job timed out")


def fetch_html(url_path):
    with urllib.request.urlopen(f"{BASE}{url_path}", timeout=30) as resp:
        return resp.read().decode()


def check(label, html, must, must_not):
    ok = True
    for s in must:
        if s not in html:
            print(f"FAIL [{label}] missing: {s!r}")
            ok = False
    for s in must_not:
        if s in html:
            print(f"FAIL [{label}] leaked: {s!r}")
            ok = False
    if ok:
        print(f"OK   [{label}]")
    return ok


def main():
    token = login("SplitTest")
    result = submit_horary(token)
    meta = result.get("meta") or {}
    print("META answer gated:", meta.get("answer"))
    print("META verdicts gated:", meta.get("verdicts"))
    free = fetch_html(result["links"]["free"])
    paid = fetch_html(result["links"]["paid"]) if result.get("paid") else None

    ok = True
    ok &= check("free", free,
                 ["Western — in plain words", "Vedic — three classical systems",
                  "In the full reading", "Unlock — ₹", "data-unlock"],
                 ["verdict-line", "Final verdict", "Full working",
                  "Timing (all three systems)", "What actually moves this"])

    if not result.get("paid"):
        if meta.get("answer") not in (None, {}):
            print("FAIL [meta] answer should be null for unpaid")
            ok = False
        if meta.get("verdicts"):
            print("FAIL [meta] verdicts should be empty for unpaid")
            ok = False

    # Admin gets paid half immediately in dev if entitled — guest won't.
    # Re-login as admin to inspect paid half.
    admin = req("POST", "/api/auth/admin", {
        "username": "graharekha", "password": "graharekha123"})
    admin_token = admin["token"]
    admin_result = submit_horary(admin_token)
    paid_html = fetch_html(admin_result["links"]["paid"])
    ok &= check("paid", paid_html,
                 ["verdict-line", "Final verdict", "Western — in plain words"],
                 ["Full working", "In the full reading",
                  '<a class="cta" href="#unlock"'])

    print("RESULT", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
