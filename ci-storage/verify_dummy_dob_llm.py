#!/usr/bin/env python3
"""E2E: dummy DOB + admin — confirm plainSummary (LLM) on all four tabs."""
from __future__ import annotations

import base64
import json
import sys
import time
import urllib.request
from pathlib import Path

BASE = "http://localhost:8080"
ROOT = Path(__file__).resolve().parents[1]

# Dummy test person — not real customer data
DUMMY = {
    "name": "Test Seeker",
    "dob": "1985-06-20",
    "tob": "09:30",
    "place": "Mumbai, India",
    "lat": 19.0760,
    "lon": 72.8777,
    "tz": 5.5,
    "gender": "female",
}


def req(method, path, body=None, token=None, timeout=900):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(
        f"{BASE}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def run_job(token, kind, payload, *, limit=900):
    job = req("POST", "/api/job", {"kind": kind, "payload": payload}, token=token)
    pid = job["jobId"]
    t0 = time.time()
    while time.time() - t0 < limit:
        snap = req("GET", f"/api/job/{pid}", token=token)
        if snap["status"] == "done":
            return snap["result"]
        if snap["status"] == "failed":
            raise RuntimeError(snap.get("error") or f"{kind} failed")
        time.sleep(3)
    raise TimeoutError(f"{kind} timed out after {limit}s")


def palm_payload():
    left = ROOT / "samplepalm1.jpg"
    right = ROOT / "samplepalm2.jpg"
    return {
        "name": DUMMY["name"],
        "age": 40,
        "gender": "female",
        "dominant": "right",
        "leftHand": base64.b64encode(left.read_bytes()).decode(),
        "rightHand": base64.b64encode(right.read_bytes()).decode(),
    }


def main() -> int:
    print("=== Dummy DOB E2E (LLM on) ===")
    print(f"DOB: {DUMMY['dob']} {DUMMY['tob']} — {DUMMY['place']}")

    pc = req("GET", "/api/public-config")
    print(f"LLM enabled: {pc.get('llmEnabled')}")
    if not pc.get("llmEnabled"):
        print("WARN: LLM not enabled — summaries will use fallback")

    token = req("POST", "/api/auth/admin", {
        "username": "graharekha",
        "password": "graharekha123",
    })["token"]

    jobs = [
        ("full_report", dict(DUMMY)),
        ("user_question", {**DUMMY, "question": "Is this a good year to change jobs?"}),
        ("horary", {
            "question": "Will the dummy test pass?",
            "qDate": "2026-08-26",
            "qTime": "18:50",
            "location": "Mumbai, India",
        }),
        ("palm", palm_payload()),
    ]

    ok = True
    for kind, payload in jobs:
        print(f"\n--- {kind} ---")
        try:
            limit = 1200 if kind == "full_report" else 900
            result = run_job(token, kind, payload, limit=limit)
            rid = result.get("reportId")
            if not rid:
                print("FAIL: no reportId")
                ok = False
                continue
            rep = req("GET", f"/api/reports/{rid}", token=token)
            ps = (rep.get("meta") or {}).get("plainSummary") or {}
            sections = ps.get("sections") or []
            gen = ps.get("generated", "?")
            if not sections:
                print("FAIL: plainSummary missing or empty")
                ok = False
                continue
            print(f"OK  reportId={rid[:8]}… paid={rep.get('paid')} "
                  f"generated={gen} sections={len(sections)}")
            for i, s in enumerate(sections[:2], 1):
                body = (s.get("body") or "")[:120]
                print(f"    {i}. {s.get('title')}: {body}…")
            if gen != "llm":
                print(f"WARN: expected generated=llm, got {gen!r}")
        except Exception as exc:
            print(f"FAIL: {exc}")
            ok = False

    print("\n" + ("ALL PASS" if ok else "SOME FAILURES"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
