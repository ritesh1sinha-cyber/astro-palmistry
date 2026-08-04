#!/usr/bin/env python3
"""Every test suite in this repo, one command, one summary.

    python3 run_tests.py             # everything except the slow API check
    python3 run_tests.py --fast      # skip the flagship report (~1 min saved)
    python3 run_tests.py --api http://localhost:8080   # add the HTTP check too

Each suite is a separate process, so one crash cannot take the rest down and the
exit code still means something. Suites that need a dependency you do not have
(PyJHora, an API) are reported as SKIP rather than failure — a runner that cries
wolf gets ignored, and then it is worse than nothing.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASTRO = HERE / "engines" / "astro"


def have(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except Exception:                                                # noqa: BLE001
        return False


# (label, argv, needs)  — `needs` is a module that must be importable
SUITES: list[tuple[str, list[str], str]] = [
    ("promo codes and the bundle", [sys.executable, "core/promo_test.py"], ""),
    ("queue serialises real DB types",
     [sys.executable, "core/queue_test.py"], ""),
    ("no-longevity chokepoint",
     [sys.executable, "engines/astro/no_longevity.py"], ""),
    ("fact guard (rewrites keep facts)",
     [sys.executable, "engines/astro/report_fact_guard.py"], ""),
    ("anchor engine not overfitted",
     [sys.executable, "engines/astro/anchor_engine_test.py"], ""),
    ("lane leaks and all 9 lanes voting",
     [sys.executable, "engines/astro/lane_sweep_test.py"], "jhora"),
    ("card design renders per kind",
     [sys.executable, "engines/astro/report_render_test.py"], ""),
    # `import X if cond else None` is not valid Python — an import is a
    # statement, not an expression. Real newlines, so the 3.9 shim can load
    # conditionally before the engine import.
    ("palm ↔ astro bridge",
     [sys.executable, "-c", "\n".join((
         "import sys",
         "sys.path.insert(0, 'engines/astro')",
         "if sys.version_info < (3, 10):",
         "    import _py39_shim",
         "import palm_astro_bridge as B",
         "sys.exit(B.selftest())",
     ))], "jhora"),
]

SLOW = ("the design is what gets STORED (end to end)",
        [sys.executable, "e2e_design.py"], "jhora")


def env_for_children() -> dict:
    env = dict(os.environ)
    env.setdefault("DEV_LOGIN", "1")
    env.setdefault("APP_SECRET", "run-tests-local-only")
    env.setdefault("ENV", "dev")
    # Same PyJHora resolution as e2e_design, so a child that needs the ephemeris
    # finds it without the reader exporting anything.
    if not env.get("PYJHORA_SRC"):
        try:
            spec = importlib.util.find_spec("jhora")
            if spec and spec.origin:
                env["PYJHORA_SRC"] = str(Path(spec.origin).parent.parent)
        except Exception:                                            # noqa: BLE001
            pass
    return env


def run(label: str, argv: list[str], needs: str, env: dict) -> tuple[str, float, str]:
    if needs and not have(needs):
        return "SKIP", 0.0, f"{needs} not installed"
    t0 = time.time()
    try:
        p = subprocess.run(argv, cwd=HERE, env=env, capture_output=True,
                           text=True, timeout=1800)
    except subprocess.TimeoutExpired:
        return "FAIL", time.time() - t0, "timed out after 30 min"
    dt = time.time() - t0
    tail = (p.stdout or "").strip().splitlines()
    summary = ""
    for line in reversed(tail):
        if "passed" in line or "VERDICT" in line:
            summary = line.strip()
            break
    if p.returncode != 0 and not summary:
        summary = ((p.stderr or "").strip().splitlines() or [""])[-1][:110]
    return ("PASS" if p.returncode == 0 else "FAIL"), dt, summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true",
                    help="skip the end-to-end handler run")
    ap.add_argument("--api", default="",
                    help="also run e2e_check.py against this API base URL")
    args = ap.parse_args()

    suites = list(SUITES)
    if not args.fast:
        suites.append(SLOW)
    if args.api:
        suites.append(("HTTP API (e2e_check)",
                       [sys.executable, "e2e_check.py", "--api", args.api], ""))

    env = env_for_children()
    print(f"python {sys.version.split()[0]}  ·  "
          f"PyJHora {'found' if have('jhora') else 'MISSING'}  ·  "
          f"sentence-transformers "
          f"{'found' if have('sentence_transformers') else 'absent (lexical fallback)'}")
    if sys.version_info < (3, 10):
        print("WARNING: some engine files need Python 3.10+. Expect failures.")
    print("=" * 78)

    rows = []
    for label, argv, needs in suites:
        print(f"  running  {label} …", flush=True)
        rows.append((label, *run(label, argv, needs, env)))

    print("=" * 78)
    for label, status, dt, summary in rows:
        mark = {"PASS": "ok  ", "FAIL": "FAIL", "SKIP": "skip"}[status]
        print(f"  {mark} {label:<44} {dt:5.1f}s  {summary[:60]}")
    failed = [r[0] for r in rows if r[1] == "FAIL"]
    skipped = [r[0] for r in rows if r[1] == "SKIP"]
    print("=" * 78)
    print(f"{sum(1 for r in rows if r[1] == 'PASS')} passed, "
          f"{len(failed)} failed, {len(skipped)} skipped")
    if failed:
        print("\nFAILED:")
        for f in failed:
            print(f"   {f}")
        print("\nRe-run one on its own to see the detail, e.g.:")
        print(f"   {sys.executable} engines/astro/report_render_test.py")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
