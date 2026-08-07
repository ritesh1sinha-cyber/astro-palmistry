#!/usr/bin/env python3
"""
audit_report_quality.py — measure presentation defects across every astro tab.

Runs each tab with a dummy chart against the local API and reports, per tab:
  styleBlocks  how many <style> tags ended up in one document (>1 == nested docs)
  h1           how many <h1> (>1 == several documents pasted together)
  lockLeak     the paywall teaser leaked into the PAID half
  words        length of the paid half
  dupLead      the personal opening repeated

Usage:  python ci-storage/audit_report_quality.py --api http://127.0.0.1:8080
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

DUMMY = {
    "name": "Test Seeker",
    "dob": "1990-04-15",
    "tob": "10:30",
    "place": "New Delhi, India",
    "lat": 17.385, "lon": 78.4867, "tz": 5.5,
    "gender": 0,
}


def req(api, path, body=None, token="", method=None):
    url = api.rstrip("/") + path
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method or ("POST" if data else "GET"))
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(r, timeout=120) as f:
            raw = f.read().decode("utf-8", "replace")
            return f.status, (json.loads(raw) if raw.startswith(("{", "[")) else raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw


def run_job(api, token, kind, payload, budget=600):
    code, res = req(api, "/api/job", {"kind": kind, "payload": payload}, token)
    if code != 200:
        return f"submit-{code}", {"error": res}
    jid = res["jobId"]
    t0 = time.time()
    while time.time() - t0 < budget:
        time.sleep(2)
        code, snap = req(api, f"/api/job/{jid}", token=token)
        if code != 200:
            return f"poll-{code}", {"error": snap}
        if snap.get("status") in ("done", "failed", "cancelled"):
            return snap["status"], snap
    return "timeout", {}


LOCK = "more sections in the full report"


def measure(html: str) -> dict:
    body = re.sub(r"<(style|script)\b.*?</\1>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", body)
    words = len(text.split())
    leads = re.findall(r"you asked about|Here is the straight answer", html)
    return {
        "styleBlocks": len(re.findall(r"<style\b", html, re.I)),
        "h1": len(re.findall(r"<h1\b", html, re.I)),
        "docs": len(re.findall(r"<html\b", html, re.I)),
        "lockLeak": LOCK in html,
        "words": words,
        "dupLead": len(leads),
    }


def fetch(api, url):
    if url.startswith("/"):
        url = api.rstrip("/") + url
    code, res = req(api, url.replace(api.rstrip("/"), "")) if url.startswith(api) else (0, "")
    return res if isinstance(res, str) else ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default=os.getenv("API", "http://127.0.0.1:8080"))
    a = ap.parse_args()

    code, res = req(a.api, "/api/auth/admin",
                    {"username": os.getenv("ADMIN_USERNAME", "graharekha"),
                     "password": os.getenv("ADMIN_PASSWORD", "graharekha123")})
    if code != 200:
        print(f"admin login failed {code}: {res}")
        return 1
    token = res["token"]
    print(f"signed in as admin ({res['user']['email']})\n")

    tabs = [
        ("numerology", {"name": DUMMY["name"], "dob": DUMMY["dob"]}),
        ("daily", dict(DUMMY)),
        ("btr", {**DUMMY, "events": [{"type": "job", "date": "2014-07-01"},
                                     {"type": "marriage", "date": "2019-02-10"}]}),
        ("muhurat", {**DUMMY, "eventId": "marriage", "date": "2026-11-20"}),
        ("kundali_match", {
            "groomName": "Groom Test", "groomDob": DUMMY["dob"],
            "groomTob": DUMMY["tob"], "groomLat": DUMMY["lat"],
            "groomLon": DUMMY["lon"], "groomTz": DUMMY["tz"],
            "groomPlace": DUMMY["place"],
            "brideName": "Bride Test", "brideDob": "1992-09-02",
            "brideTob": "06:15", "brideLat": DUMMY["lat"],
            "brideLon": DUMMY["lon"], "brideTz": DUMMY["tz"],
            "bridePlace": DUMMY["place"]}),
        ("horary", {"question": "Will the new product sell well?",
                    "qDate": time.strftime("%Y-%m-%d"),
                    "qTime": time.strftime("%H:%M:%S"),
                    "location": "New Delhi, India",
                    "lat": 17.385, "lon": 78.4867, "tz": 5.5, "kpNumber": 108}),
        ("full_report", dict(DUMMY)),
    ]

    rows = []
    for kind, payload in tabs:
        t0 = time.time()
        status, snap = run_job(a.api, token, kind, payload)
        took = time.time() - t0
        if status != "done":
            rows.append((kind, status, {}, took))
            print(f"{kind:14s} {status}  ({took:.0f}s)  {str(snap)[:200]}")
            continue
        result = snap.get("result") or {}
        links = result.get("links") or {}
        paid_url = links.get("paid") or links.get("free") or ""
        html = ""
        if paid_url:
            _, html = req(a.api, paid_url, token=token)
            if not isinstance(html, str):
                html = json.dumps(html)
        m = measure(html)
        rows.append((kind, status, m, took))
        print(f"{kind:14s} ok  ({took:.0f}s)  docs={m['docs']} style={m['styleBlocks']} "
              f"h1={m['h1']} lockLeak={m['lockLeak']} words={m['words']} "
              f"dupLead={m['dupLead']}")

    print("\n--- summary (defect = docs>1 or style>1 or h1>1 or lockLeak) ---")
    for kind, status, m, took in rows:
        if not m:
            print(f"  {kind}: {status}")
            continue
        bad = m["docs"] > 1 or m["styleBlocks"] > 1 or m["h1"] > 1 or m["lockLeak"]
        print(f"  {kind}: {'NEEDS REWORK' if bad else 'clean'}  ({m['words']} words)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
