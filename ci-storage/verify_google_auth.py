#!/usr/bin/env python3
"""Smoke-test Google Sign-In wiring (no real Google login required)."""
import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8123"
EXPECTED_SUFFIX = ".apps.googleusercontent.com"


def get(path):
    with urllib.request.urlopen(f"{BASE}{path}", timeout=15) as resp:
        return json.loads(resp.read().decode())


def post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE}{path}", data=data,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def main():
    cfg = get("/api/public-config")
    cid = cfg.get("googleClientId") or ""
    if not cid.endswith(EXPECTED_SUFFIX):
        print(f"FAIL public-config googleClientId missing or invalid: {cid!r}")
        return 1
    print(f"OK   public-config exposes client id ({cid[:12]}...)")

    code, body = post("/api/auth/google", {"idToken": "not-a-jwt"})
    if code == 503 and "not configured" in body:
        print("FAIL google auth still reports GOOGLE_CLIENT_ID not configured")
        return 1
    if code != 401:
        print(f"FAIL bad token should 401, got {code}: {body[:120]}")
        return 1
    print("OK   /api/auth/google verifies tokens (401 on junk token)")

    print("RESULT PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
