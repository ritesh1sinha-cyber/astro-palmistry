"""API smoke test for reports list + PDF (run inside container)."""
import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8080"


def post(path, body):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def get(path, token):
    req = urllib.request.Request(
        BASE + path,
        headers={"Authorization": "Bearer " + token},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(), r.headers


token = post("/api/auth/admin", {"username": "graharekha", "password": "graharekha123"})[
    "token"
]
rows = json.loads(
    urllib.request.urlopen(
        urllib.request.Request(
            BASE + "/api/reports?paid=1",
            headers={"Authorization": "Bearer " + token},
        ),
        timeout=30,
    ).read().decode()
)
assert isinstance(rows, list), rows
print("paid_reports", len(rows))
if not rows:
    print("api_smoke: skip pdf (no paid reports)")
    raise SystemExit(0)
rid = rows[0]["reportId"]
kind = rows[0].get("kind")
print("sample", rid, kind, "links.paid=", bool((rows[0].get("links") or {}).get("paid")))
pdf_bytes, headers = get(f"/api/reports/{rid}/pdf", token)
assert headers.get("Content-Type", "").startswith("application/pdf"), headers.get(
    "Content-Type"
)
assert len(pdf_bytes) > 1000, len(pdf_bytes)
print("api_smoke: OK pdf_bytes=", len(pdf_bytes))
