"""Inspect cached overlays matching the latest paid hash."""
import json, subprocess

out = subprocess.run(
    ["docker", "exec", "astro-palmistry-local-redis-1", "redis-cli",
     "--scan", "--pattern", "llm:v2:*:full_report:paid"],
    capture_output=True, text=True
)
keys = [k for k in out.stdout.splitlines() if k.strip()]
print(f"{len(keys)} paid cache keys")
for key in keys:
    res = subprocess.run(
        ["docker", "exec", "astro-palmistry-local-redis-1", "redis-cli", "GET", key],
        capture_output=True, text=True
    )
    try:
        data = json.loads(res.stdout)
    except Exception:
        print("  (unreadable)", key)
        continue
    overlay = data.get("overlay") or {}
    areas = overlay.get("areas") or {}
    with_concl = [k for k, v in areas.items()
                  if isinstance(v, dict) and str(v.get("conclusion") or "").strip()]
    stats = data.get("stats") or {}
    print(f"\nKEY hash={key.split(':')[2]} accepted={stats.get('accepted')} "
          f"rejected={stats.get('rejected')} areas={len(areas)} "
          f"with_conclusion={len(with_concl)}")
    if with_concl:
        for k in with_concl[:2]:
            print(f"  [{k}] {areas[k].get('conclusion', '')[:200]}")
    rr = stats.get("rejection_reasons") or {}
    if rr:
        top = dict(list(rr.items())[:8])
        print("  rejection reasons:", top)