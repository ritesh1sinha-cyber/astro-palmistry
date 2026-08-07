#!/usr/bin/env python3
"""Verify the daily reading's free/paid split.

Free is taster-forever: the verdict, the Moon proof block, the lucky number and
colour, and one Do / one Don't. Everything that explains *why* today reads that
way is the subscription.

The assertions match real markup rather than bare class names. Both halves carry
the whole shared stylesheet, so `"lanes"` or `"palm-points"` would match a CSS
rule in either document and pass for the wrong reason.
"""
import json
import sys
import time
import urllib.error
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


def req(method, path, body=None, token=None, timeout=120):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers,
                               method=method)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def login(name="Guest"):
    return req("POST", "/api/auth/dev", {
        "name": name, "email": f"{name.lower().replace(' ', '')}@guest.local",
        "passcode": "graharekha",
    })["token"]


def submit_daily(token):
    job = req("POST", "/api/job", {"kind": "daily", "payload": dict(SAMPLE)},
              token=token)
    pid = job["jobId"]
    for _ in range(120):
        snap = req("GET", f"/api/job/{pid}", token=token, timeout=120)
        if snap["status"] == "done":
            return snap["result"]
        if snap["status"] == "failed":
            raise RuntimeError(snap.get("error") or "job failed")
        time.sleep(2)
    raise TimeoutError("daily job timed out")


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


# Markup that only exists when the block actually rendered.
LANE_TABLE = '<ul class="lanes">'
DASHA_ROWS = "The clock you are actually running on"
AV_BLOCK = "Ashtakavarga on today's transit houses"
AV_LORDS = "Your dasha lords, where they are today"
HOUSES = "The houses that are lit today"
WINDOWS = '<ul class="windows">'
WINDOWS_HEADING = "Best and avoid times"
EXTRAS = '<details class="workings workings-main">'
PROOF = '<div class="proof">'
LUCKY = "Your number and colour for today"
DODONT = '<div class="dodont">'
CTA = 'data-unlock="1"'
LOCKED_PREVIEW = "What the subscription adds each morning"
TECHNICAL = "<b>Technical basis:</b>"


def main():
    ok = True

    print("Submitting daily as guest...")
    token = login("DailySplit")
    result = submit_daily(token)
    if result.get("locked"):
        print("FAIL [free] daily still returns a hard quota block")
        return 1
    free = fetch_html(result["links"]["free"])

    ok &= check(
        "free", free,
        [PROOF, LUCKY, DODONT, CTA, LOCKED_PREVIEW,
         "measured from your birth",
         "Daily reading · today&#x27;s verdict, free"],
        [LANE_TABLE, DASHA_ROWS, AV_BLOCK, AV_LORDS, HOUSES, WINDOWS, EXTRAS,
         "Mahadasha:", "How these were derived</span>\n    <ul>"])

    # The paid half must not even be linked for a guest.
    if "paid" not in (result.get("links") or {}):
        print("OK   [free] no paid link handed to an unsubscribed reader")
    else:
        try:
            fetch_html(result["links"]["paid"])
            print("FAIL [free] paid link readable without a subscription")
            ok = False
        except urllib.error.HTTPError as exc:
            print(f"OK   [free] paid link gated ({exc.code})")

    print("Submitting daily as admin...")
    admin = req("POST", "/api/auth/admin",
                {"username": "graharekha", "password": "graharekha123"})
    admin_result = submit_daily(admin["token"])
    paid = fetch_html(admin_result["links"]["paid"])

    ok &= check(
        "paid", paid,
        [WINDOWS, WINDOWS_HEADING, TECHNICAL, PROOF, LUCKY, DODONT,
         "Daily reading · unlocked", "What to do with today"],
        [LOCKED_PREVIEW, CTA, LANE_TABLE, DASHA_ROWS, AV_BLOCK, AV_LORDS,
         HOUSES, EXTRAS, "Mahadasha:", "How these were derived"])

    # Paid must be a superset: every free block survives the unlock.
    for block in (PROOF, LUCKY, DODONT):
        if block not in paid:
            print(f"FAIL [paid] free block dropped after unlock: {block!r}")
            ok = False

    print("RESULT", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
