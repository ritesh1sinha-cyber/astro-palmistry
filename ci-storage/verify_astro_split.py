#!/usr/bin/env python3
"""Verify full_report free/paid split after paywall redesign."""
import json
import re
import sys
import time
import urllib.request

BASE = "http://localhost:8080"

SAMPLE = {
    "name": "Sample User",
    "dob": "1990-01-15",
    "tob": "12:00",
    "place": "New Delhi, India",
    "lat": 28.6139,
    "lon": 77.2090,
    "tz": 5.5,
    "gender": "male",
}

AREA_LABELS = (
    "Work &amp; Career", "Money", "Relationships &amp; Partnership", "Home &amp; Family",
    "Children", "Health &amp; Energy", "Learning &amp; Luck", "Inner Life",
)


def req(method, path, body=None, token=None, timeout=120):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def login(name="Guest"):
    return req("POST", "/api/auth/dev", {
        "name": name, "email": f"{name.lower().replace(' ', '')}@guest.local",
        "passcode": "graharekha",
    })["token"]


def submit_full_report(token, *, question=""):
    payload = dict(SAMPLE)
    if question:
        payload["question"] = question
    job = req("POST", "/api/job", {"kind": "full_report", "payload": payload}, token=token)
    pid = job["jobId"]
    for _ in range(300):
        snap = req("GET", f"/api/job/{pid}", token=token, timeout=120)
        if snap["status"] == "done":
            return snap["result"]
        if snap["status"] == "failed":
            raise RuntimeError(snap.get("error") or "job failed")
        time.sleep(3)
    raise TimeoutError("full_report job timed out")


def fetch_html(url_path):
    with urllib.request.urlopen(f"{BASE}{url_path}", timeout=60) as resp:
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


def has_unlocked_evidence(html: str) -> bool:
    return "How this chapter affects this area" in html


def has_unlocked_when(html: str) -> bool:
    return bool(re.search(r'<div class="when">[^<]', html))


def main():
    print("Submitting full_report as guest (sample DOB New Delhi)...")
    token = login("AstroSplit")
    result = submit_full_report(token)
    free = fetch_html(result["links"]["free"])

    ok = True
    ok &= check("free", free,
                 ["locked-inline", "data-unlock", "lock-blur",
                  'class="present-current"', "recognition", "Unlock full reading"]
                 + list(AREA_LABELS),
                 ["<ol class=\"timeline\">", "<ol class=\"windows-list\">", "Full working",
                  "Planets involved", "How this chapter affects this area", "Your life promises"])
    if has_unlocked_evidence(free):
        print("FAIL [free] leaked unlocked evidence <ul>")
        ok = False
    else:
        print("OK   [free] evidence locked")
    if has_unlocked_when(free):
        print("FAIL [free] leaked unlocked <div class=\"when\">")
        ok = False
    else:
        print("OK   [free] per-card dates locked")

    print("Submitting full_report as admin...")
    admin = req("POST", "/api/auth/admin", {
        "username": "graharekha", "password": "graharekha123"})
    admin_result = submit_full_report(admin["token"])
    paid_html = fetch_html(admin_result["links"]["paid"])
    ok &= check("paid", paid_html,
                 ["<ol class=\"timeline\">", "<ol class=\"windows-list\">",
                  "Your life promises", "Planets involved", "How this chapter affects this area"],
                 ["Full working", "What the full reading adds"])
    if not has_unlocked_evidence(paid_html):
        print("FAIL [paid] missing evidence lists")
        ok = False
    else:
        print("OK   [paid] evidence present")
    if not has_unlocked_when(paid_html):
        print("FAIL [paid] missing dated windows")
        ok = False
    else:
        print("OK   [paid] dated windows present")

    print("RESULT", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
