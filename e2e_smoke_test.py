"""End-to-end smoke test for the paid report pipeline."""
import requests, json, time, re, sys

BASE = "http://localhost:8080"

# Step 1: Dev login
r = requests.post(f"{BASE}/api/auth/dev", json={"passcode": "graharekha"})
token = r.json().get("token")
headers = {"Authorization": f"Bearer {token}"}
print("[1] Login OK")

# Step 2: Submit full_report job
payload = {
    "name": "E2E Test",
    "dob": "1988-11-22",
    "tob": "14:15",
    "place": "Delhi, India",
    "lat": 28.7041,
    "lon": 77.1025,
    "tz": 5.5,
    "gender": 1,
}
r = requests.post(f"{BASE}/api/job", json={"kind": "full_report", "payload": payload}, headers=headers)
job = r.json()
job_id = job["jobId"]
print(f"[2] Job: {job_id}")

# Step 3: Poll
for i in range(150):
    time.sleep(2)
    r = requests.get(f"{BASE}/api/job/{job_id}", headers=headers)
    job = r.json()
    if i % 5 == 0:
        print(f"[3] {(i+1)*2}s status={job['status']}")
    if job["status"] == "done":
        print(f"[3] DONE in {(i+1)*2}s")
        break
    elif job["status"] in ("failed", "error"):
        print(f"[3] FAILED: {job}")
        sys.exit(1)
else:
    print("[3] TIMEOUT")
    sys.exit(1)

# Step 4: Fetch report
report_id = job["result"]["reportId"]
r = requests.get(f"{BASE}/api/reports/{report_id}", headers=headers)
report = r.json()
paid_url = report["links"]["paid"]
if paid_url.startswith("/"):
    paid_url = BASE + paid_url
r = requests.get(paid_url, headers=headers)
html = r.text
print(f"[4] Paid HTML: {len(html)} chars")

# Step 5: Validation
print()
print("=== VALIDATION ===")
failures = []

# Placeholder check
placeholders = [
    "This remedy is linked to a relevant chart factor",
    "The chart evidence is summarized in the life-area reading above",
    "Timing evidence is included in the overall reading",
    "Promised, not yet active",
    "Full analyst working",
    "pending LLM prose",
    "awaiting humanization",
    "[pending", "[placeholder", "[TODO", "[INTERNAL",
    "Raw classical wording", "Existing chart-rule", "internal rule id",
]
found = [p for p in placeholders if p.lower() in html.lower()]
if found:
    print(f"PLACEHOLDER TEXT: FAIL - {found}")
    failures.append("placeholders")
else:
    print("Placeholder text: PASS (0 found)")

# Internal data leakage
internal = [
    "ashtakavarga", "navamsha_grids", "raw_score",
    "planetary_dignity_score", "house_lordship_score", "sign_dispositor_score",
]
leaked = [t for t in internal if t.lower() in html.lower()]
if leaked:
    print(f"INTERNAL DATA LEAKAGE: FAIL - {leaked}")
    failures.append("internal_leakage")
else:
    print("Internal data leakage: PASS (0 found)")

# Jargon abbr title check
abbr_titles = re.findall(r'<abbr[^>]*title="([^"]+)"', html)
if abbr_titles:
    print(f"JARGON ABBR TITLES: {len(abbr_titles)} remaining")
    for t in abbr_titles[:5]:
        print(f'  "{t}"')
    failures.append("abbr_titles")
else:
    print("Jargon abbr titles: PASS (0 remaining)")

# Guarantee language
guarantees = ["guarantee", "guaranteed", "100% sure", "definitely will"]
found_g = [g for g in guarantees if g.lower() in html.lower()]
if found_g:
    print(f"GUARANTEE LANGUAGE: FAIL - {found_g}")
    failures.append("guarantees")
else:
    print("Guarantee language: PASS")

# Duplicate section check
health_count = len(re.findall(r"<h[23][^>]*>[^<]*Health[^<]*</h[23]>", html, re.I))
if health_count > 1:
    print(f"DUPLICATE SECTIONS: FAIL - {health_count} Health headers")
    failures.append("duplicate_sections")
else:
    print(f"Duplicate section check: PASS ({health_count} Health header)")

# Remedy count
remedy_count = html.lower().count("remedy")
print(f"Remedy mentions: {remedy_count}")

print()
if failures:
    print(f"=== E2E SMOKE TEST: FAIL ({len(failures)} issues) ===")
    print(f"   Failed: {failures}")
    sys.exit(1)
else:
    print("=== E2E SMOKE TEST: ALL PASS ===")
    sys.exit(0)
