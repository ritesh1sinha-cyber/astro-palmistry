#!/usr/bin/env python3
"""Verify the palm free/paid split after the cards-v2 paywall redesign.

Runs a real palm job end to end as a guest and as an admin, then asserts on the
two stored HTML halves. Assertions that depend on what the CV actually detected
(dated markings, special marks) are reported but only enforced when the data is
there, so a thin photo does not produce a false failure. The gate itself —
verdict free, working paid, paid a superset — is always enforced.
"""
import base64
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

BASE = "http://localhost:8080"
FIX = Path(__file__).resolve().parent.parent / "fixtures"
LEFT = FIX / "real_left.jpg"
RIGHT = FIX / "real_right.jpg"

UNLOCKED_EVIDENCE = re.compile(
    r'<div class="evidence"><span class="ev-label">What your hands show</span>')
AREA = re.compile(r'<span class="area">([^<]+)</span>')
CUSTOMER_JUNK = ("triplicity", "chart-from-palm", "weekday-born", "phalange count")


def req(method, path, body=None, token=None, timeout=120):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers,
                               method=method)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def login(name):
    return req("POST", "/api/auth/dev", {
        "name": name, "email": f"{name.lower()}@guest.local",
        "passcode": "graharekha",
    })["token"]


def b64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode("ascii")


def submit(token):
    job = req("POST", "/api/job", {
        "kind": "palm",
        "payload": {
            "name": "Sample User", "age": 34, "gender": "male",
            "dominant": "right",
            "leftHand": b64(LEFT), "rightHand": b64(RIGHT),
        },
    }, token=token)
    pid = job["jobId"]
    for _ in range(200):
        snap = req("GET", f"/api/job/{pid}", token=token)
        if snap["status"] == "done":
            return snap["result"]
        if snap["status"] == "failed":
            raise RuntimeError(snap.get("error") or "job failed")
        time.sleep(3)
    raise TimeoutError("palm job timed out")


def fetch(url_path):
    with urllib.request.urlopen(f"{BASE}{url_path}", timeout=60) as resp:
        return resp.read().decode()


class Check:
    def __init__(self):
        self.ok = True

    def has(self, label, html, needle):
        if needle in html:
            print(f"OK   [{label}] has {needle!r}")
        else:
            print(f"FAIL [{label}] missing {needle!r}")
            self.ok = False

    def lacks(self, label, html, needle):
        if needle in html:
            print(f"FAIL [{label}] leaked {needle!r}")
            self.ok = False
        else:
            print(f"OK   [{label}] no {needle!r}")

    def want(self, cond, label, msg):
        if cond:
            print(f"OK   [{label}] {msg}")
        else:
            print(f"FAIL [{label}] {msg}")
            self.ok = False


def main():
    for p in (LEFT, RIGHT):
        if not p.is_file():
            print(f"FAIL missing fixture {p} — copy a left and a right palm photo there")
            return 1

    print("Submitting palm job as guest...")
    free = fetch(submit(login("PalmSplit"))["links"]["free"])
    print("Submitting palm job as admin...")
    admin = req("POST", "/api/auth/admin",
                {"username": "graharekha", "password": "graharekha123"})
    paid = fetch(submit(admin["token"])["links"]["paid"])

    c = Check()

    # the old template must be gone from both halves
    for label, html in (("free", free), ("paid", paid)):
        c.lacks(label, html, "report-card")
        c.lacks(label, html, "Palmistry analysis report")

    # free: verdicts and photographs present, working absent
    c.has("free", free, "locked-inline")
    c.has("free", free, "data-unlock")
    c.has("free", free, "lock-blur")
    c.has("free", free, "palm-imgs")
    c.has("free", free, "Left hand")
    c.has("free", free, "Right hand")
    c.has("free", free, "evidence locked-inline")
    # Always present: it is built from hand shape, thumb and fingers, not from
    # the dated markings, which the engine only produces for the major lines.
    c.has("free", free, 'class="proof"')
    c.has("free", free, '<ul class="hits">')
    # Match markup, not class names: both halves carry the whole shared
    # stylesheet, so a bare "palm-points" hits the CSS rule in either one.
    c.lacks("free", free, '<ol class="timeline">')
    c.lacks("free", free, '<ul class="palm-points">')
    c.lacks("free", free, '<span class="pt-when">')
    c.lacks("free", free, '<details class="workings')
    c.want(not UNLOCKED_EVIDENCE.search(free), "free",
           "no unlocked evidence list under any card")

    # paid: everything unlocked, and it is a superset
    c.has("paid", paid, "palm-imgs")
    c.has("paid", paid, "Left hand")
    c.has("paid", paid, "Right hand")
    c.has("paid", paid, '<ul class="palm-points">')
    c.has("paid", paid, '<details class="workings')
    c.has("paid", paid, "Mount by mount")
    c.has("paid", paid, 'class="proof"')
    c.lacks("paid", paid, "What the full reading adds")
    c.lacks("paid", paid, "evidence locked-inline")
    c.lacks("paid", paid, 'data-unlock="1"')
    c.want(bool(UNLOCKED_EVIDENCE.search(paid)), "paid",
           "evidence lists present under the cards")

    for label, html in (("free", free), ("paid", paid)):
        for phrase in CUSTOMER_JUNK:
            c.lacks(label, html.lower(), phrase)

    # the free half must hide no life area
    free_areas, paid_areas = set(AREA.findall(free)), set(AREA.findall(paid))
    c.want(free_areas and free_areas == paid_areas, "areas",
           f"{len(free_areas)} life areas, identical in both halves")
    if free_areas != paid_areas:
        print("     free only:", sorted(free_areas - paid_areas))
        print("     paid only:", sorted(paid_areas - free_areas))

    # Data-dependent: an age past every dated marking, or a photo with no marks
    # on it, legitimately empties these. Report, do not fail.
    for label, needle, what in (
            ("paid", '<ol class="timeline">', "forward timeline"),
            ("paid", "special marks", "mark meanings")):
        html = free if label == "free" else paid
        found = needle.lower() in html.lower()
        print(f"{'OK  ' if found else 'note'} [{label}] {what} "
              f"{'present' if found else 'absent (nothing detected)'}")

    print("RESULT", "PASS" if c.ok else "FAIL")
    return 0 if c.ok else 1


if __name__ == "__main__":
    sys.exit(main())
