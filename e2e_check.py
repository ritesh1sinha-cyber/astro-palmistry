#!/usr/bin/env python3
"""
e2e_check.py — end-to-end verification of the production stack.

Exercises every paid path AND tries to break the paywall. Exits non-zero on any
failure, so it works as a post-deploy gate in CI.

    python3 e2e_check.py --api https://your-domain \
        --left left.jpg --right right.jpg \
        --dob 1990-01-15 --tob 12:00 --lat 28.6139 --lon 77.2090

Auth uses /api/auth/dev, which requires DEV_LOGIN=1 (never set in production).
Against a production host, pass --token from a real signed-in session instead.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

PASS, FAIL, SKIP = "\033[92m PASS\033[0m", "\033[91m FAIL\033[0m", "\033[93m SKIP\033[0m"
results: list[tuple[str, object]] = []


def say(name: str, ok, note: str = "") -> None:
    results.append((name, ok))
    tag = PASS if ok else (SKIP if ok is None else FAIL)
    print(f"{tag}  {name}" + (f"  — {note}" if note else ""), flush=True)


class Api:
    def __init__(self, base: str, token: str = "") -> None:
        self.base = base.rstrip("/")
        self.token = token

    def __call__(self, path, body=None, method=None, raw=False, expect=None):
        req = urllib.request.Request(
            self.base + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Content-Type": "application/json",
                     **({"Authorization": "Bearer " + self.token} if self.token else {})},
            method=method or ("POST" if body is not None else "GET"))
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                return r.read() if raw else json.load(r)
        except urllib.error.HTTPError as e:
            if expect and e.code == expect:
                return {"_status": e.code}
            return {"_status": e.code, "_body": e.read().decode()[:200]}

    def run(self, kind, payload, limit=900):
        j = self(f"/api/job", {"kind": kind, "payload": payload})
        if "_status" in j:
            return j
        t0 = time.time()
        while j.get("status") in ("queued", "processing") and time.time() - t0 < limit:
            time.sleep(2)
            j = self(f"/api/job/{j['jobId']}")
        return j


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--api", required=True)
    p.add_argument("--token", default="")
    p.add_argument("--left"); p.add_argument("--right")
    p.add_argument("--name", default="E2E Test")
    p.add_argument("--dob", default="1990-01-15")
    p.add_argument("--tob", default="12:00")
    p.add_argument("--place", default="New Delhi, India")
    p.add_argument("--lat", type=float, default=28.6139)
    p.add_argument("--lon", type=float, default=77.2090)
    p.add_argument("--tz", type=float, default=5.5)
    p.add_argument("--age", type=int, default=41)
    p.add_argument("--full-report", action="store_true")
    a = p.parse_args()

    api = Api(a.api, a.token)

    # ---------------------------------------------------------------- health
    h = api("/health")
    say("health", bool(h.get("ok")), f"env={h.get('env')}")
    if not h.get("ok"):
        return summary()

    # ------------------------------------------------------------------ auth
    if not api.token:
        r = api("/api/auth/dev", {"email": f"e2e-{int(time.time())}@test.local",
                                  "name": a.name,
                                  "passcode": os.getenv("GUEST_PASSCODE", "graharekha")})
        if "_status" in r:
            say("auth", None, "pass --token, or set DEV_LOGIN=1 on a dev host")
            return summary()
        api.token = r["token"]
        say("auth", True, r["user"]["email"])
    me = api("/api/me")
    say("session works", "email" in me,
        f"subscribed {bool(me.get('subscribed'))}, horary left {me.get('horaryLeft')}")

    birth = {"name": a.name, "dob": a.dob, "tob": a.tob, "place": a.place,
             "lat": a.lat, "lon": a.lon, "tz": a.tz, "gender": 0}

    # ------------------------------------------------------ free: chart + cache
    t0 = time.time()
    j = api.run("chart_summary", birth)
    cold = time.time() - t0
    lag = ((j.get("result") or {}).get("lagna") or {}).get("sign")
    say("chart summary (free)", j.get("status") == "done" and bool(lag),
        f"lagna {lag}")
    note = (j.get("result") or {}).get("personalNote") or ""
    say("reading is personalised", a.name.split()[0] in note,
        "opens with the person's name and their own chart facts")

    t0 = time.time()
    j2 = api.run("chart_summary", birth)
    warm = time.time() - t0
    say("precompute cache reused", j2.get("status") == "done",
        f"{cold:.2f}s → {warm:.2f}s")

    say("numerology (free)", api.run("numerology", birth).get("status") == "done")

    # -------------------------------------------------------------- horary
    j = api.run("horary", {"question": "Will this deployment hold?",
                           "qDate": time.strftime("%Y-%m-%d"),
                           "qTime": time.strftime("%H:%M"), "location": a.place})
    res = j.get("result") or {}
    v = (res.get("meta") or {}).get("verdicts") or {}
    vd, wd = v.get("vedic") or {}, v.get("western") or {}
    say("horary: both traditions", j.get("status") == "done",
        f"vedic {vd.get('verdict') or vd.get('error')} / western {wd.get('verdict') or wd.get('error')}")
    say("vedic horary renders", not vd.get("error"),
        "upstream glyph bug — is ASTRO_HOTFIX=1?" if vd.get("error") else "")
    rid = res.get("reportId")
    say("paid half withheld", not res.get("paid"))

    # ------------------------------------------------- THE SECURITY CHECKS
    if rid:
        rep = api(f"/api/reports/{rid}")
        links = rep.get("links") or {}
        say("free half served", len(api(links["free"], raw=True)) > 500)
        forged = links["free"].replace(".free.", ".paid.")
        say("forged paid link rejected",
            api(forged, expect=403).get("_status") in (402, 403),
            "signature check holds")
        say("full report blocked before payment",
            api(f"/api/reading/{rid}/full", expect=402).get("_status") == 402)

        o = api("/api/order", {"item": "horary", "refId": rid})
        say("order created", bool(o.get("orderId")), f"₹{o.get('amount')}")
        wh = api("/api/payment/webhook", {"orderId": o["orderId"]})
        if wh.get("_status") == 401:
            say("unsigned webhook rejected", True, "correct in production")
            say("paid unlock", None, "needs a real signed gateway webhook")
        else:
            say("webhook granted access", bool(wh.get("ok")))
            rep2 = api(f"/api/reports/{rid}")
            say("paid half unlocked", rep2.get("paid") and "paid" in rep2["links"])
            if rep2.get("paid"):
                say("paid bytes served",
                    len(api(rep2["links"]["paid"], raw=True)) > 500)

    # ----------------------------------------------------- matching / muhurat
    j = api.run("kundali_match", {
        "groomName": a.name, "groomDob": a.dob, "groomTob": a.tob,
        "groomPlace": a.place, "groomLat": a.lat, "groomLon": a.lon, "groomTz": a.tz,
        "brideName": "Partner", "brideDob": "1988-07-22", "brideTob": "09:40",
        "bridePlace": "Ranchi", "brideLat": 23.3441, "brideLon": 85.3096, "brideTz": 5.5})
    m = (j.get("result") or {}).get("meta") or {}
    say("kundali matching", j.get("status") == "done",
        f"{m.get('total')}/{m.get('maxGuna')} guna, {len(m.get('paidSections') or [])} paid sections")

    ev = api.run("muhurat_events", {})
    say("muhurat catalogue", (ev.get("result") or {}).get("events") is not None,
        f"{len((ev.get('result') or {}).get('events') or [])} occasions")
    j = api.run("muhurat", dict(birth, eventId="marriage", date="2026-11-20"))
    mr = j.get("result") or {}
    say("muhurat check", j.get("status") == "done",
        (mr.get("meta") or {}).get("verdict") or mr.get("reportId"))
    say("muhurat cards-v2", (mr.get("meta") or {}).get("design") == "cards-v2"
        and bool((mr.get("links") or {}).get("free")))

    # ------------------------------------------------------------------ BTR
    j = api.run("btr", dict(birth, events={"marriage": "2013-02-15",
                                           "first_job": "2007-08-01",
                                           "child": "2016-06-10",
                                           "higher_education": "2003-07-15"}))
    b = j.get("result") or {}
    say("birth-time check", j.get("status") == "done",
        f"{b.get('trialTime')} moves {b.get('movesBy')}, changes lagna={b.get('changesLagna')}")
    say("btr paid answer withheld", b.get("suggestedTime") is None)
    say("btr cards-v2", (b.get("meta") or {}).get("design") == "cards-v2"
        and bool((b.get("links") or {}).get("free")))

    # ---------------------------------------------------------------- daily
    seen_lock = False
    daily_ok = False
    for i in range(5):
        d = (api.run("daily", birth).get("result") or {})
        if d.get("links") and d.get("reportId"):
            daily_ok = (d.get("meta") or {}).get("design") == "cards-v2"
        if d.get("locked"):
            seen_lock = True
            break
    say("daily cards-v2", daily_ok)
    say("free daily quota enforced", seen_lock, "locks after the free allowance")

    # ---------------------------------------------------------------- palm
    if a.left and a.right:
        with open(a.left, "rb") as f:
            left = base64.b64encode(f.read()).decode()
        with open(a.right, "rb") as f:
            right = base64.b64encode(f.read()).decode()
        j = api.run("palm", {"name": a.name, "age": a.age, "gender": "male",
                             "dominant": "right", "leftHand": left, "rightHand": right})
        r = j.get("result") or {}
        say("palm reading", j.get("status") == "done", j.get("error") or "")
        if j.get("status") == "done":
            meta = r.get("meta") or {}
            links = r.get("links") or {}
            free_html = api(links["free"], raw=True) if links.get("free") else b""
            if isinstance(free_html, bytes):
                free_html = free_html.decode("utf-8", errors="replace")
            say("palm cards-v2", meta.get("design") == "cards-v2")
            say("palm free report has both hands",
                "Left hand" in free_html and "Right hand" in free_html)
            say("palm free evidence stays locked",
                "evidence locked-inline" in free_html and '<ul class="palm-points">' not in free_html)
            say("palm report excludes astro-palm jargon",
                not any(term in free_html.lower() for term in
                        ("triplicity", "chart-from-palm", "weekday-born", "phalange count")))
            say("palm overlays stored", bool(r.get("overlays")))
    else:
        say("palm reading", None, "pass --left and --right")

    # --------------------------------------------------------- full report
    if a.full_report:
        j = api.run("full_report", birth, limit=1200)
        m = (j.get("result") or {}).get("meta") or {}
        say("full confluence report", j.get("status") == "done",
            j.get("error") or f"{len(m.get('freeSections') or [])} free / "
                              f"{len(m.get('paidSections') or [])} paid sections")
    else:
        say("full confluence report", None, "add --full-report (1–3 min, needs torch)")

    # ------------------------------------------------- no citations anywhere
    scan_citations(api)

    say("queue drained", sum((api("/api/queue").get("depth") or {}).values()) == 0)
    return summary()


# Anything here appearing in a customer-facing reading is a leak: the product
# sells a reading of their hand or chart, not a bibliography.
CITATION_BLOCKLIST = [
    "Palmistry for All", "Modern Case Studies", "Succinct Palmistry",
    "Practical Handbook", "Samudrik", "Apprentice to Pro",
    "Secrets of Profession", "Principles of Self-Learning",
    "How to Master", "All the Secrets",
    "Horary Astrology Plain", "Integrated Approach",
    "Cheiro", "Lilly", "Louis", "Bonatus", "Bhardwaj", "Narasimha Rao",
    "Avasthi", "Manley", "Sanjay Rath", "Rangacharya",
    "Krishnamurti", "Jaimini", "Parashari", "Parashara", "BNN",
    "book-backed", "book-sourced", "book rule", "book precedent",
    "no LLM", "NO LLM", "deterministic rule engine", "Uncalibrated",
    "corpus", "OCR",
]
PAGE_PATTERNS = [r"\bpp?\.\s?\d+", r"\bpage\s+\d+"]


def scan_citations(api) -> None:
    """Download every report half this run produced and scan the bytes."""
    import re as _re
    reports = api("/api/reports")
    if not isinstance(reports, list) or not reports:
        say("no citations in output", None, "no reports to scan")
        return
    leaks, scanned = {}, 0
    for rep in reports:
        for half, link in (rep.get("links") or {}).items():
            body = api(link, raw=True)
            if not isinstance(body, bytes):
                continue
            scanned += 1
            text = body.decode("utf-8", "ignore")
            for term in CITATION_BLOCKLIST:
                if term.lower() in text.lower():
                    leaks.setdefault(term, []).append(f"{rep['kind']}/{half}")
            for pat in PAGE_PATTERNS:
                m = _re.search(pat, text, _re.I)
                if m:
                    leaks.setdefault(m.group(0), []).append(f"{rep['kind']}/{half}")
    if leaks:
        detail = "; ".join(f"{k} in {v[0]}" for k, v in list(leaks.items())[:4])
        say("no citations in output", False, f"{len(leaks)} leaked — {detail}")
    else:
        say("no citations in output", True,
            f"{scanned} report halves scanned, no book/author/page reference")


def summary() -> int:
    ok = sum(1 for _, v in results if v is True)
    bad = sum(1 for _, v in results if v is False)
    skip = sum(1 for _, v in results if v is None)
    print(f"\n\033[1m{ok} passed, {bad} failed, {skip} skipped\033[0m")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
