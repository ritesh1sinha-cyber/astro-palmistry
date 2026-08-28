#!/usr/bin/env python3
"""Verify plainSummary on full_report, palm, horary, user_question (admin account)."""
from __future__ import annotations

import base64
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://localhost:8080"
ROOT = Path(__file__).resolve().parents[1]

SAMPLE = {
    "name": "Summary E2E",
    "dob": "1990-01-15",
    "tob": "12:00",
    "place": "New Delhi, India",
    "lat": 28.6139,
    "lon": 77.2090,
    "tz": 5.5,
    "gender": "male",
}


def req(method, path, body=None, token=None, timeout=900):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(
        f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_txt = e.read().decode()[:400]
        raise RuntimeError(f"HTTP {e.code} {path}: {body_txt}") from e


def admin_login():
    return req("POST", "/api/auth/admin", {
        "username": "graharekha",
        "password": "graharekha123",
    })["token"]


def run_job(token, kind, payload, *, limit=900):
    job = req("POST", "/api/job", {"kind": kind, "payload": payload}, token=token)
    pid = job["jobId"]
    t0 = time.time()
    while time.time() - t0 < limit:
        snap = req("GET", f"/api/job/{pid}", token=token)
        if snap["status"] == "done":
            return snap["result"]
        if snap["status"] == "failed":
            raise RuntimeError(snap.get("error") or f"{kind} job failed")
        time.sleep(3)
    raise TimeoutError(f"{kind} job timed out after {limit}s")


def check_plain_summary(kind: str, meta: dict) -> bool:
    ps = (meta or {}).get("plainSummary") or {}
    sections = ps.get("sections") or []
    gen = ps.get("generated") or "?"
    if not sections:
        print(f"FAIL [{kind}] plainSummary missing or empty")
        return False
    bad = [s for s in sections if not (s.get("title") or "").strip()
           or not (s.get("body") or "").strip()]
    if bad:
        print(f"FAIL [{kind}] section(s) missing title/body")
        return False
    titles = [s["title"] for s in sections[:3]]
    print(f"OK   [{kind}] plainSummary ({gen}) — {len(sections)} section(s): "
          f"{', '.join(titles)}")
    return True


def palm_payload():
    left = ROOT / "samplepalm1.jpg"
    right = ROOT / "samplepalm2.jpg"
    if not left.is_file() or not right.is_file():
        raise FileNotFoundError("samplepalm1.jpg / samplepalm2.jpg required at repo root")
    return {
        "name": SAMPLE["name"],
        "age": 35,
        "gender": "male",
        "dominant": "right",
        "leftHand": base64.b64encode(left.read_bytes()).decode(),
        "rightHand": base64.b64encode(right.read_bytes()).decode(),
    }


def main() -> int:
    print("Checking API health…")
    try:
        h = req("GET", "/health")
    except Exception as exc:
        print(f"FAIL health: {exc}")
        return 1
    if not h.get("ok"):
        print(f"FAIL health: {h}")
        return 1
    print(f"OK   health env={h.get('env')}")

    print("Logging in as admin…")
    token = admin_login()
    me = req("GET", "/api/me", token=token)
    print(f"OK   admin session {me.get('email')}")

    ok = True
    jobs = [
        ("full_report", dict(SAMPLE)),
        ("user_question", {**SAMPLE, "question": "When is the best time for a career move?"}),
        ("horary", {
            "question": "Will this plain summary feature work end to end?",
            "qDate": "2026-08-26",
            "qTime": "14:30",
            "location": "New Delhi, India",
        }),
        ("palm", palm_payload()),
    ]

    for kind, payload in jobs:
        print(f"\nSubmitting {kind}…")
        try:
            if kind == "full_report":
                result = run_job(token, kind, payload, limit=1200)
            else:
                result = run_job(token, kind, payload)
        except Exception as exc:
            print(f"FAIL [{kind}] job: {exc}")
            ok = False
            continue
        rid = result.get("reportId")
        if not rid:
            print(f"FAIL [{kind}] no reportId in result")
            ok = False
            continue
        rep = req("GET", f"/api/reports/{rid}", token=token)
        meta = rep.get("meta") or result.get("meta") or {}
        ok &= check_plain_summary(kind, meta)
        if not rep.get("paid") and kind != "horary":
            print(f"WARN [{kind}] admin report not marked paid (summary may use free half)")

    print("\n" + ("ALL PASS" if ok else "SOME FAILURES"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
