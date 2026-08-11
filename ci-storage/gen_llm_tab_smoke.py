"""Smoke-test palm / horary / user_question / chat with LLM enabled.

Host-side: hits local Docker API for horary, user_question, chat.
Palm HTML is generated inside the API container from mounted photos.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / "ci-storage"
OUT = CI / "review_html" / "llm_smoke"
COMPRESSED = Path(r"C:\Users\IN009287\Downloads\Compressed\latest\review_html")
CONTAINER = "astro-palmistry-local-api-1"
BASE = "http://localhost:8080"
RIGHT = Path(r"C:\Users\IN009287\Downloads\R.jpg")
LEFT = Path(r"C:\Users\IN009287\Downloads\L.jpg")

MEERA = {
    "name": "Meera Nair",
    "dob": "1990-01-15",
    "tob": "12:00",
    "lat": 28.6139,
    "lon": 77.2090,
    "tz": 5.5,
    "place": "New Delhi",
    "gender": 0,
}


def _req(method: str, path: str, body=None, token: str | None = None, timeout=180):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(
        f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        raise RuntimeError(f"{method} {path} -> {e.code}: {detail}") from e


def _fetch(path: str) -> str:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=60) as resp:
        return resp.read().decode("utf-8", "replace")


def _run(cmd: list[str], *, check: bool = True) -> int:
    print("+", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, check=False)
    if check and r.returncode != 0:
        raise SystemExit(r.returncode)
    return r.returncode


def login() -> str:
    return _req("POST", "/api/auth/dev", {
        "name": "LLMSmoke",
        "email": "llmsmoke@guest.local",
        "passcode": "graharekha",
    })["token"]


def wait_job(token: str, job_id: str, *, seconds: int = 600) -> dict:
    for _ in range(max(1, seconds // 3)):
        snap = _req("GET", f"/api/job/{job_id}", token=token, timeout=120)
        st = snap.get("status")
        if st == "done":
            return snap.get("result") or {}
        if st == "failed":
            raise RuntimeError(snap.get("error") or "job failed")
        time.sleep(3)
    raise TimeoutError(f"job {job_id} timed out")


def unlock_if_needed(token: str, result: dict) -> dict:
    """Dev auto-pay path so paid HTML + chat are available."""
    rid = result.get("reportId")
    if not rid:
        return result
    if result.get("paid") and (result.get("links") or {}).get("paid"):
        return result
    # Create order + complete-dev when available
    try:
        order = _req("POST", "/api/order", {
            "item": result.get("kind") or "full_report",
            "refId": rid,
        }, token=token)
        public_id = order.get("publicId") or order.get("orderId")
        if public_id:
            _req("POST", f"/api/order/{public_id}/complete-dev", {}, token=token)
            return _req("GET", f"/api/reports/{rid}", token=token)
    except Exception as exc:  # noqa: BLE001
        print(f"[unlock] skipped: {exc}", flush=True)
    return result


def save_pair(kind: str, free: str, paid: str | None, meta: dict) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    COMPRESSED.mkdir(parents=True, exist_ok=True)
    free_p = OUT / f"{kind}_free.html"
    paid_p = OUT / f"{kind}_paid.html"
    meta_p = OUT / f"{kind}_meta.json"
    free_p.write_text(free, encoding="utf-8")
    if paid:
        paid_p.write_text(paid, encoding="utf-8")
    meta_p.write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    for p in (free_p, paid_p, meta_p):
        if p.is_file():
            shutil.copy2(p, COMPRESSED / p.name)
            shutil.copy2(p, CI / "review_html" / p.name)
    return {
        "free": str(free_p),
        "paid": str(paid_p) if paid else None,
        "free_bytes": len(free),
        "paid_bytes": len(paid or ""),
        "llm": (meta or {}).get("llm") or {},
    }


def test_public_config() -> dict:
    cfg = _req("GET", "/api/public-config")
    print("public-config:", json.dumps({
        "llmEnabled": cfg.get("llmEnabled"),
        "chatEnabled": cfg.get("chatEnabled"),
    }), flush=True)
    if not cfg.get("llmEnabled"):
        raise RuntimeError("LLM_ENABLED is off — set .env and recreate api")
    return cfg


def test_horary(token: str) -> dict:
    print("\n=== HORARY ===", flush=True)
    job = _req("POST", "/api/job", {
        "kind": "horary",
        "payload": {
            "question": "Will this job offer come through this year?",
            "qDate": "2026-08-11",
            "qTime": "18:00",
            "location": "New Delhi, India",
            "kpNumber": "108",
        },
    }, token=token)
    result = wait_job(token, job["jobId"], seconds=420)
    result = unlock_if_needed(token, result)
    links = result.get("links") or {}
    free = _fetch(links["free"]) if links.get("free") else ""
    paid = _fetch(links["paid"]) if links.get("paid") else ""
    meta = result.get("meta") or {}
    out = save_pair("horary_llm", free, paid or None, meta)
    out["reportId"] = result.get("reportId")
    out["llm_enabled"] = bool((meta.get("llm") or {}).get("enabled"))
    out["has_prose_hint"] = any(
        x in (paid or free)
        for x in ("Ask about", "verdict", "reading leans", "combined")
    )
    print(json.dumps({k: out[k] for k in (
        "reportId", "llm_enabled", "free_bytes", "paid_bytes", "llm")},
        default=str), flush=True)
    return out


def test_user_question(token: str) -> dict:
    print("\n=== USER QUESTION ===", flush=True)
    payload = dict(MEERA)
    payload["question"] = "Will my career improve in the next two years?"
    payload["area"] = "profession"
    job = _req("POST", "/api/job", {
        "kind": "user_question",
        "payload": payload,
    }, token=token)
    result = wait_job(token, job["jobId"], seconds=600)
    result = unlock_if_needed(token, result)
    links = result.get("links") or {}
    free = _fetch(links["free"]) if links.get("free") else ""
    paid = _fetch(links["paid"]) if links.get("paid") else ""
    meta = result.get("meta") or {}
    out = save_pair("user_question_llm", free, paid or None, meta)
    out["reportId"] = result.get("reportId")
    out["llm_enabled"] = bool((meta.get("llm") or {}).get("enabled"))
    out["llm"] = meta.get("llm") or {}
    print(json.dumps({k: out[k] for k in (
        "reportId", "llm_enabled", "free_bytes", "paid_bytes", "llm")},
        default=str), flush=True)
    return out


def test_palm() -> dict:
    print("\n=== PALMISTRY ===", flush=True)
    if not RIGHT.is_file() or not LEFT.is_file():
        return {"ok": False, "error": "missing R.jpg / L.jpg"}
    _run(["docker", "exec", CONTAINER, "mkdir", "-p", "/tmp/palm_in", "/tmp/palm_out"])
    _run(["docker", "cp", str(RIGHT), f"{CONTAINER}:/tmp/palm_in/R.jpg"])
    _run(["docker", "cp", str(LEFT), f"{CONTAINER}:/tmp/palm_in/L.jpg"])
    # Inline generator inside container (uses mounted engines/core)
    script = r'''
import json, sys
from pathlib import Path
sys.path[:0] = ["/app", "/app/engines", "/app/engines/astro"]
from palm_api.pipeline import analyze_image_paths
from core.palm_report import build_palm_html_reading
out = Path("/tmp/palm_out")
out.mkdir(parents=True, exist_ok=True)
overlays = out / "overlays"
overlays.mkdir(parents=True, exist_ok=True)
raw = analyze_image_paths(
    ["/tmp/palm_in/R.jpg", "/tmp/palm_in/L.jpg"],
    active_hand="right", overlay_dir=overlays)
free, paid, meta = build_palm_html_reading(
    raw, {"name":"Meera","age":30,"gender":"female","dominant":"right"}, price=499)
(out / "meera_palm_llm_free.html").write_text(free, encoding="utf-8")
(out / "meera_palm_llm_paid.html").write_text(paid, encoding="utf-8")
(out / "meera_palm_llm_meta.json").write_text(
    json.dumps(meta, indent=2, default=str), encoding="utf-8")
print(json.dumps({
    "free_bytes": len(free), "paid_bytes": len(paid),
    "llm": meta.get("llm") or {},
    "aspects": len((raw.get("confluence") or {}).get("life_aspects") or []),
}))
'''
    gen_path = CI / "_palm_llm_once.py"
    gen_path.write_text(script, encoding="utf-8")
    _run(["docker", "cp", str(gen_path), f"{CONTAINER}:/tmp/_palm_llm_once.py"])
    print("Waiting 35s for rate-limit window before palm…", flush=True)
    time.sleep(35)
    proc = subprocess.run(
        ["docker", "exec", "-e", "LLM_CONCURRENCY=1", CONTAINER,
         "python", "/tmp/_palm_llm_once.py"],
        check=False, capture_output=True, text=True)
    print(proc.stdout[-2000:] if proc.stdout else "", flush=True)
    if proc.returncode != 0:
        print(proc.stderr[-2000:] if proc.stderr else "", flush=True)
        return {"ok": False, "error": "palm generator failed", "code": proc.returncode}
    OUT.mkdir(parents=True, exist_ok=True)
    for name in (
        "meera_palm_llm_free.html",
        "meera_palm_llm_paid.html",
        "meera_palm_llm_meta.json",
    ):
        _run(["docker", "cp", f"{CONTAINER}:/tmp/palm_out/{name}", str(OUT / name)])
        shutil.copy2(OUT / name, CI / "review_html" / name)
        shutil.copy2(OUT / name, COMPRESSED / name)
    meta = json.loads((OUT / "meera_palm_llm_meta.json").read_text(encoding="utf-8"))
    try:
        summary = json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        summary = {"llm": meta.get("llm") or {}}
    summary["ok"] = True
    summary["llm_enabled"] = bool((meta.get("llm") or {}).get("enabled"))
    print(json.dumps(summary, indent=2), flush=True)
    return summary


def test_chat(token: str, report_id: str) -> dict:
    print("\n=== CHAT ===", flush=True)
    cfg = _req("GET", "/api/public-config")
    if not cfg.get("chatEnabled"):
        return {"ok": False, "error": "chatEnabled=false"}
    hist = _req("GET", f"/api/reports/{report_id}/chat", token=token)
    ans = _req("POST", f"/api/reports/{report_id}/chat", {
        "message": "What does my career / work area say about the next two years?",
    }, token=token)
    out = {
        "ok": True,
        "reportId": report_id,
        "history_n": len((hist or {}).get("messages") or []),
        "out_of_scope": bool(ans.get("out_of_scope")),
        "answer": (ans.get("answer") or "")[:280],
        "used_fact_ids": ans.get("used_fact_ids") or [],
    }
    (OUT / "chat_smoke.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    shutil.copy2(OUT / "chat_smoke.json", COMPRESSED / "chat_smoke.json")
    print(json.dumps(out, indent=2), flush=True)
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    summary: dict = {"ok": True, "tabs": {}}
    try:
        cfg = test_public_config()
        summary["config"] = {
            "llmEnabled": cfg.get("llmEnabled"),
            "chatEnabled": cfg.get("chatEnabled"),
        }
        token = login()
        print("Waiting 40s for LLM rate-limit window…", flush=True)
        time.sleep(40)

        h = test_horary(token)
        summary["tabs"]["horary"] = h
        time.sleep(40)

        q = test_user_question(token)
        summary["tabs"]["user_question"] = q
        time.sleep(40)

        p = test_palm()
        summary["tabs"]["palm"] = p

        # Prefer user_question report for chat (has facts_key when LLM path ran)
        rid = q.get("reportId") or h.get("reportId")
        if rid:
            time.sleep(20)
            # Ensure unlocked for chat
            try:
                rep = _req("GET", f"/api/reports/{rid}", token=token)
                if not rep.get("paid"):
                    unlock_if_needed(token, {
                        "reportId": rid,
                        "kind": "user_question",
                        "links": rep.get("links") or {},
                    })
            except Exception as exc:  # noqa: BLE001
                print(f"[chat prep] {exc}", flush=True)
            c = test_chat(token, rid)
            summary["tabs"]["chat"] = c
        else:
            summary["tabs"]["chat"] = {"ok": False, "error": "no reportId"}

    except Exception as exc:  # noqa: BLE001
        summary["ok"] = False
        summary["error"] = f"{type(exc).__name__}: {exc}"
        print("FATAL:", summary["error"], flush=True)

    # Pass criteria: each tab attempted; LLM enabled flags where applicable
    tabs = summary.get("tabs") or {}
    checks = {
        "config_llm": bool((summary.get("config") or {}).get("llmEnabled")),
        "config_chat": bool((summary.get("config") or {}).get("chatEnabled")),
        "horary_html": bool((tabs.get("horary") or {}).get("free_bytes")),
        "horary_llm": bool((tabs.get("horary") or {}).get("llm_enabled")),
        "question_html": bool((tabs.get("user_question") or {}).get("free_bytes")),
        "question_llm": bool((tabs.get("user_question") or {}).get("llm_enabled")),
        "palm_ok": bool((tabs.get("palm") or {}).get("ok")),
        "palm_llm": bool((tabs.get("palm") or {}).get("llm_enabled")),
        "chat_ok": bool((tabs.get("chat") or {}).get("ok")),
        "chat_has_answer": bool((tabs.get("chat") or {}).get("answer")),
    }
    summary["checks"] = checks
    summary["ok"] = all(checks.values())
    out_path = OUT / "llm_tab_smoke_summary.json"
    out_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    shutil.copy2(out_path, COMPRESSED / out_path.name)
    print("\n=== SUMMARY ===", flush=True)
    print(json.dumps({"ok": summary["ok"], "checks": checks}, indent=2), flush=True)
    print(f"Wrote {out_path}", flush=True)
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
