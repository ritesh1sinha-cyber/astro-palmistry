"""Fetch the latest paid report HTML and save it."""
import requests, json, time, re, sys

BASE = "http://localhost:8080"
r = requests.post(f"{BASE}/api/auth/dev", json={"passcode": "graharekha"})
token = r.json().get("token")
headers = {"Authorization": f"Bearer {token}"}

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
job_id = r.json()["jobId"]
for i in range(150):
    time.sleep(2)
    r = requests.get(f"{BASE}/api/job/{job_id}", headers=headers)
    if r.json()["status"] in ("done", "failed", "error"):
        break
report_id = r.json()["result"]["reportId"]
r = requests.get(f"{BASE}/api/reports/{report_id}", headers=headers)
paid_url = r.json()["links"]["paid"]
if paid_url.startswith("/"):
    paid_url = BASE + paid_url
html = requests.get(paid_url, headers=headers).text
with open("sample_full_report.html", "w", encoding="utf-8") as f:
    f.write(html)
print("saved", len(html), "chars")
print("report_id", report_id)