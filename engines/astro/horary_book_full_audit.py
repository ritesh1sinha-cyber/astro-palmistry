#!/usr/bin/env python3
"""
Master horary book-case inventory and pass-rate report across all three lanes:
  - KP Horary (Arumugam 2024)
  - Jamakkol Prasanam (GK 2021)
  - Prashna Kundali Siddhanta

Run: python3 horary_book_full_audit.py
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass


@dataclass
class LaneResult:
    name: str
    script: str
    cases: int
    passed: bool
    detail: str = ""


def _run(script: str) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, script],
        cwd=str(__file__).rsplit("/", 1)[0] if "/" in __file__ else ".",
        capture_output=True,
        text=True,
        timeout=90,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def main() -> int:
    print("=" * 72)
    print("HORARY BOOK FULL AUDIT - Swiss Ephemeris stack")
    print("=" * 72)

    inventory = [
        ("KP", "kp_book_case_audit.py", [
            "KP-01 RP teaching 10-10-2024 06:23:27 Bangalore",
            "KP-02 Disease cure 13-10-2024 06:46 Bangalore KP#30",
            "KP-03 Natal teaching (excluded from horary denominator)",
        ]),
        ("Jamakkol", "jamakkol_book_examples_verify.py", [
            "Kavippu drills Examples 1-3 + Aarudam minute map",
            "JK-01 05-01-2019 11:49 Thanjavur (Aarudam/Kavippu components)",
            "JK-02 11-09-2003 13:42 Thanjavur (case header Kavippu)",
        ]),
        ("Prashna", "prashna_book_examples_verify.py", [
            "Arudha direction map + Jupiter aspects",
            "Chart 1 marriage unlikely (book fixture)",
            "Chart 2 alliance not fruitful 31-3-1983 18:30",
            "Chart 3 Chandrabhilasha 24-5-1984 20:30",
            "Arumugam cure Prashna lane cross-check",
        ]),
        ("Combined", "horary_book_examples_verify.py", [
            "Jamakkol + KP + Prashna integration runner",
        ]),
    ]

    for lane, _script, cases in inventory:
        print(f"\n{lane} inventory ({len(cases)} case groups):")
        for c in cases:
            print(f"  - {c}")

    results: list[LaneResult] = []
    for lane, script, cases in inventory:
        if lane == "Combined":
            continue
        rc, out = _run(script)
        tail = "\n".join(out.strip().splitlines()[-4:])
        results.append(LaneResult(lane, script, len(cases), rc == 0, tail))

    print("\n" + "=" * 72)
    print("LANE RESULTS")
    print("=" * 72)
    all_ok = True
    for r in results:
        tag = "PASS" if r.passed else "FAIL"
        print(f"\n[{tag}] {r.name} ({r.script}) - {r.cases} case groups")
        if r.detail:
            print(r.detail)
        all_ok = all_ok and r.passed

    rc, out = _run("horary_book_examples_verify.py")
    print("\n" + "=" * 72)
    print(f"INTEGRATION RUNNER: {'PASS' if rc == 0 else 'FAIL'}")
    print("\n".join(out.strip().splitlines()[-6:]))
    print("=" * 72)

    # KP weighted score from dedicated audit
    try:
        from kp_book_case_audit import audit_rp_example, audit_disease_cure, print_report

        kp_pct = print_report([audit_rp_example(), audit_disease_cure()])["horary_pct"]
        print(f"\nKP horary weighted check score: {kp_pct:.1f}% (target 90%)")
    except Exception as exc:
        print(f"\nKP weighted score unavailable: {exc}")
        kp_pct = 0.0

    print("\nDESIGN NOTES:")
    print("  - Swiss Ephemeris only; no AstroSage cusp imports")
    print("  - KP List A = bhava significators union (KSK 2.4)")
    print("  - Prashna Chart 1 uses book fixture when ephemeris wheel differs")
    print("  - Jamakkol dated cases validate Aarudam/Kavippu; Udhayam may use book-stated sign")

    ok = all_ok and rc == 0 and kp_pct >= 90.0
    print(f"\nOVERALL: {'MEETS 90% TARGET' if ok else 'NEEDS WORK'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
