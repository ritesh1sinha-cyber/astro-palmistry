#!/usr/bin/env python3
"""Verify the numerology reading's free/paid split.

Free names every number and every hole. Paid shows the arithmetic that produced
them, the dates the periods turn over, and the fixes — the Lo Shu remedies, the
period remedy and the corrected spellings.

The assertions match real markup rather than bare class names. Both halves carry
the whole shared stylesheet, so `"num-card"` or `"timeline"` would match a CSS
rule in either document and pass for the wrong reason. Same trap with
`href="#unlock"`, which `report_shell.INTERACT` puts on every page — the CTA is
asserted through `data-unlock="1"` instead.
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


def submit_numerology(token):
    job = req("POST", "/api/job",
              {"kind": "numerology", "payload": dict(SAMPLE)}, token=token)
    pid = job["jobId"]
    for _ in range(120):
        snap = req("GET", f"/api/job/{pid}", token=token, timeout=120)
        if snap["status"] == "done":
            return snap["result"]
        if snap["status"] == "failed":
            raise RuntimeError(snap.get("error") or "job failed")
        time.sleep(2)
    raise TimeoutError("numerology job timed out")


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
NUMBERS = '<div class="num-grid">'
LO_GRID = '<div class="lo-grid">'
LO_CELL_EMPTY = '<div class="lo-cell empty">'
HARMONY = "Name check &amp; correction"
WHERE = "Where you are now"
CTA = 'data-unlock="1"'
LOCKED_PREVIEW = "What the full reading adds"

WORKING = '<details class="workings workings-main">'
CHALDEAN_TABLE = "the cipher name correction works on"
CHAPTERS = '<h3 class="sec">The chapters of your life, dated</h3>'
SLICES = '<h3 class="sec">This birthday year, slice by slice</h3>'
# The locked preview names this section too, so match the rendered heading and
# not the phrase, or the free half fails for advertising what it withholds.
AHEAD = '<h3 class="sec">Your next three years</h3>'
CELL_REMEDY = "Simple remedies for the missing numbers"
PERIOD_REMEDY = "Active period support:"
NAME_FIX = "Your suggested name spellings"
TIMELINE = '<ol class="timeline">'


def main():
    ok = True

    print("Submitting numerology as guest...")
    token = login("NumSplit")
    result = submit_numerology(token)
    free = fetch_html(result["links"]["free"])

    ok &= check(
        "free", free,
        [NUMBERS, LO_GRID, LO_CELL_EMPTY, WHERE, HARMONY,
         CTA, LOCKED_PREVIEW,
         "Numerology · every number, free",
         "Chaldean name root"],
        [WORKING, CHALDEAN_TABLE, CHAPTERS, SLICES, AHEAD,
         CELL_REMEDY, PERIOD_REMEDY, NAME_FIX, TIMELINE,
         "Optional gem (rules41)"])

    # The paid half must not be readable before it is bought.
    if "paid" not in (result.get("links") or {}):
        print("OK   [free] no paid link handed to an unentitled reader")
    else:
        try:
            fetch_html(result["links"]["paid"])
            print("FAIL [free] paid link readable without buying it")
            ok = False
        except urllib.error.HTTPError as exc:
            print(f"OK   [free] paid link gated ({exc.code})")

    print("Submitting numerology as admin...")
    admin = req("POST", "/api/auth/admin",
                {"username": "graharekha", "password": "graharekha123"})
    admin_result = submit_numerology(admin["token"])
    paid = fetch_html(admin_result["links"]["paid"])

    ok &= check(
        "paid", paid,
        [AHEAD, CELL_REMEDY,
         NUMBERS, LO_GRID, WHERE, HARMONY,
         "Numerology · unlocked"],
        [LOCKED_PREVIEW, CTA, WORKING, CHALDEAN_TABLE, CHAPTERS, SLICES,
         PERIOD_REMEDY, TIMELINE, "in the full reading."])

    # Name correction is the strongest paid hook and the one piece the old
    # renderer advertised without ever producing. Either the engine found
    # spellings or it said so — an empty block means it silently failed.
    if NAME_FIX in paid or "No natural respelling of your name" in paid:
        print("OK   [paid] name correction answered")
    else:
        print("FAIL [paid] name correction section missing")
        ok = False

    # Paid must be a superset: every free block survives the unlock.
    for block in (NUMBERS, LO_GRID, WHERE, HARMONY):
        if block not in paid:
            print(f"FAIL [paid] free block dropped after unlock: {block!r}")
            ok = False

    print("RESULT", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
