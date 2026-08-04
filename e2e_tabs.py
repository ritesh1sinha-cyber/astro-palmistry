"""Drive every tab of the site against a live API with real birth data.

`e2e_check.py` proves the plumbing works — auth, paywall, quotas, signed links.
This proves the *product* works: it submits the job behind every tab, waits for
the real engines, saves what came back, and reports what a customer would
actually receive.

Charts used (real people, real coordinates — placeholders hide nothing):
    Ritesh   8 Mar 1985, 13:05, Patna
    Aditi   29 Jul 1989, 00:05, Patna       (for kundali matching)

Usage:
    python3 e2e_tabs.py --api http://127.0.0.1:8123 --out /tmp/e2e_out
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PATNA = {"lat": 25.5941, "lon": 85.1376, "tz": 5.5, "place": "Patna, Bihar, India"}

RITESH = {"name": "Ritesh", "dob": "1985-03-08", "tob": "13:05", "gender": "male",
          **PATNA}
ADITI = {"name": "Aditi", "dob": "1989-07-29", "tob": "00:05", "gender": "female",
         **PATNA}


def _req(api: str, path: str, *, token: str = "", method: str = "GET",
         body: dict | None = None, timeout: int = 300):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(api + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw.strip().startswith(("{", "["))
                              else raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw


def login(api: str) -> str:
    email = f"tabs-{int(time.time())}@test.local"
    code, res = _req(api, "/api/auth/dev", method="POST",
                     body={"email": email, "name": "Ritesh"})
    if code != 200:
        sys.exit(f"dev login failed ({code}): {res}")
    return res["token"]


def run_job(api: str, token: str, kind: str, payload: dict,
            *, budget: int = 420) -> tuple[str, dict]:
    """Submit, poll to completion, return (status, result)."""
    code, res = _req(api, "/api/job", token=token, method="POST",
                     body={"kind": kind, "payload": payload})
    if code != 200:
        return f"submit-{code}", {"error": res}
    pid = res["jobId"]
    started = time.time()
    while time.time() - started < budget:
        time.sleep(2)
        code, snap = _req(api, f"/api/job/{pid}", token=token)
        if code != 200:
            return f"poll-{code}", {"error": snap}
        status = snap.get("status")
        if status in ("done", "failed", "cancelled"):
            return status, snap
    return "timeout", {}


# --- the tabs ---------------------------------------------------------------

def tabs() -> list[tuple[str, str, dict]]:
    """(tab label, job kind, payload) — one entry per thing a user can click."""
    chart = {"name": RITESH["name"], "dob": RITESH["dob"], "tob": RITESH["tob"],
             "lat": RITESH["lat"], "lon": RITESH["lon"], "tz": RITESH["tz"],
             "place": RITESH["place"], "gender": RITESH["gender"]}
    return [
        ("Chart snapshot", "chart_summary", dict(chart)),
        # with a question: the full report answers it too, and that path was
        # never exercised until this line existed
        ("Full report", "full_report", dict(
            chart, question="Will my career move forward this year?")),
        # horaryPayload(): a horary chart is cast for the MOMENT OF ASKING,
        # so it takes the question's date/time/place, not the birth details.
        ("Ask a question", "horary", {
            "question": "Will I change my job in the next twelve months?",
            "qDate": "2026-08-04", "qTime": "09:40",
            "location": "Patna, India"}),
        ("Daily reading", "daily", dict(chart)),
        ("Numerology", "numerology", {
            "name": "Ritesh Sinha", "dob": RITESH["dob"]}),
        ("Kundali matching", "kundali_match", {
            "groomName": RITESH["name"], "groomDob": RITESH["dob"],
            "groomTob": RITESH["tob"], "groomLat": RITESH["lat"],
            "groomLon": RITESH["lon"], "groomTz": RITESH["tz"],
            "groomPlace": RITESH["place"],
            "brideName": ADITI["name"], "brideDob": ADITI["dob"],
            "brideTob": ADITI["tob"], "brideLat": ADITI["lat"],
            "brideLon": ADITI["lon"], "brideTz": ADITI["tz"],
            "bridePlace": ADITI["place"],
            "method": "North"}),
        ("Muhurat — event list", "muhurat_events", {}),
        ("Muhurat", "muhurat", {
            **chart, "eventId": "marriage", "date": "2026-11-20"}),
        # NOTE: priced in the front-end config (₹199) but no tab submits it.
        ("Future event timing", "future_event", {
            **chart, "eventType": "promotion"}),
        # exactly the shape site/index.html btrPayload() posts
        ("Birth-time check", "btr", {
            **chart, "events": {"first_job": "2007-08-01",
                                "marriage": "2011-02-13",
                                "child": "2014-06-01",
                                "higher_education": "2005-07-15",
                                "foreign_travel": ""}}),
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://127.0.0.1:8123")
    ap.add_argument("--out", default="/tmp/e2e_out")
    ap.add_argument("--only", default="", help="substring filter on tab name")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    code, health = _req(args.api, "/health")
    if code != 200:
        sys.exit(f"api not healthy: {code} {health}")
    token = login(args.api)
    print(f"api {args.api}  ok\n")

    rows = []
    for label, kind, payload in tabs():
        if args.only and args.only.lower() not in label.lower():
            continue
        t0 = time.time()
        status, snap = run_job(args.api, token, kind, payload)
        secs = time.time() - t0
        result = (snap or {}).get("result") or {}
        err = (snap or {}).get("error") or (result.get("error") if
                                            isinstance(result, dict) else None)

        blob = json.dumps(result, indent=2, default=str)
        (out / f"{kind}.json").write_text(blob)

        # Reports are delivered as signed links, not inline HTML — so the
        # first version of this script "passed" without ever seeing a word of
        # what the customer reads. Follow the links.
        html_files = []
        if isinstance(result, dict):
            for key, v in (result.get("links") or {}).items():
                code_h, body = _req(args.api, v, token=token)
                if code_h == 200 and isinstance(body, str) and len(body) > 200:
                    p = out / f"{kind}.{key}.html"
                    p.write_text(body)
                    html_files.append(p.name)
            for key in ("freeHtml", "paidHtml", "html"):
                v = result.get(key)
                if isinstance(v, str) and "<" in v and len(v) > 200:
                    p = out / f"{kind}.{key}.html"
                    p.write_text(v)
                    html_files.append(p.name)

        rows.append({"tab": label, "kind": kind, "status": status,
                     "secs": round(secs, 1), "error": err,
                     "keys": sorted(result)[:8] if isinstance(result, dict) else [],
                     "html": html_files,
                     "bytes": len(blob)})
        mark = "ok  " if status == "done" and not err else "FAIL"
        print(f"{mark} {label:<24} {kind:<16} {secs:>6.1f}s  "
              f"{len(blob):>8,}B  {','.join(html_files) or '-'}")
        if err:
            print(f"       error: {str(err)[:300]}")

    (out / "summary.json").write_text(json.dumps(rows, indent=2, default=str))
    good = sum(1 for r in rows if r["status"] == "done" and not r["error"])
    print(f"\n{good}/{len(rows)} tabs returned a result   → {out}")
    return 0 if good == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
