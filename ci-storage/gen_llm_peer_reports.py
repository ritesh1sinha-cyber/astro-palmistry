"""Generate Meera/Ramesh/Suresh/Gyanesh peer HTML with current LLM settings.

Runs inside the local Docker API container (via host-side docker exec/cp).
Does not fail the whole batch if interactive checklist warnings fire —
HTML is still collected for peer review.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / "ci-storage"
REVIEW = CI / "review_html"
OVERSAMPLE = CI / "oversample"
CONTAINER = "astro-palmistry-local-api-1"
COMPRESSED = Path(r"C:\Users\IN009287\Downloads\Compressed\latest\review_html")


def _run(cmd: list[str], *, check: bool = True) -> int:
    print("+", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, check=False)
    if check and r.returncode != 0:
        raise SystemExit(r.returncode)
    return r.returncode


def main() -> int:
    REVIEW.mkdir(parents=True, exist_ok=True)
    OVERSAMPLE.mkdir(parents=True, exist_ok=True)
    COMPRESSED.mkdir(parents=True, exist_ok=True)

    # Ensure openai is present (image may predate requirements.api.txt pin).
    _run([
        "docker", "exec", CONTAINER, "pip", "install", "-q", "openai>=1.40",
    ], check=False)

    for script in ("gen_interactive_review.py", "gen_oversample_reports.py"):
        _run(["docker", "cp", str(CI / script), f"{CONTAINER}:/tmp/{script}"])

    print("Waiting 40s for LLM rate-limit window…", flush=True)
    time.sleep(40)

    # Meera — keep HTML even if checklist fails under LLM wording
    code = _run(
        ["docker", "exec", "-e", "LLM_CONCURRENCY=1", CONTAINER,
         "python", "/tmp/gen_interactive_review.py"],
        check=False,
    )
    print(f"[meera] generator exit={code}", flush=True)

    print("Waiting 45s before oversample charts…", flush=True)
    time.sleep(45)

    code = _run(
        ["docker", "exec", "-e", "LLM_CONCURRENCY=1", CONTAINER,
         "python", "/tmp/gen_oversample_reports.py"],
        check=False,
    )
    print(f"[oversample] generator exit={code}", flush=True)

    copies = [
        (f"{CONTAINER}:/tmp/review_samples/astro_full_report_free.html",
         CI / "astro_full_report_free.html",
         "meera_1990-01-15_delhi_free.html"),
        (f"{CONTAINER}:/tmp/review_samples/astro_full_report_paid.html",
         CI / "astro_full_report_paid.html",
         "meera_1990-01-15_delhi_paid.html"),
    ]
    for src, dst, alias in copies:
        _run(["docker", "cp", src, str(dst)])
        shutil.copy2(dst, REVIEW / dst.name)
        shutil.copy2(dst, REVIEW / alias)
        shutil.copy2(dst, COMPRESSED / dst.name)
        shutil.copy2(dst, COMPRESSED / alias)

    for slug in (
        "ramesh_1986-03-08_delhi",
        "suresh_1990-01-12_delhi",
        "gyanesh_2012-01-01_hyderabad",
    ):
        for tier in ("free", "paid"):
            name = f"{slug}_{tier}.html"
            src = f"{CONTAINER}:/tmp/review_samples/oversample/{name}"
            dst = OVERSAMPLE / name
            _run(["docker", "cp", src, str(dst)])
            shutil.copy2(dst, REVIEW / name)
            shutil.copy2(dst, COMPRESSED / name)

    _run([
        "docker", "cp",
        f"{CONTAINER}:/tmp/review_samples/oversample/index.json",
        str(OVERSAMPLE / "index.json"),
    ], check=False)

    # Spot-check LLM acceptance lines from container logs (best-effort)
    _run([
        "docker", "logs", "--tail", "80", CONTAINER,
    ], check=False)

    print("LLM peer reports written to:", REVIEW, COMPRESSED, flush=True)
    for p in sorted(REVIEW.glob("*_{free,paid}.html")) if False else []:
        pass
    for p in sorted(REVIEW.iterdir()):
        if p.suffix == ".html" and any(
            x in p.name for x in ("meera_1990", "ramesh_", "suresh_", "gyanesh_", "astro_full")
        ):
            print(f"  {p.name}  {p.stat().st_size} bytes", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
