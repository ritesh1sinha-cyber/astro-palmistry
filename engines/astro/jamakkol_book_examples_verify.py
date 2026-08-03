#!/usr/bin/env python3
"""Jamakkol Prasanam (GK 2021) book-example validation."""
from __future__ import annotations

import sys

from horary_precompute import (
    get_aarudam,
    get_veedhi,
    get_kavippu,
    jamakkol_udhayam_method1,
    precompute_horary,
    julian_day,
    ist_to_ut,
)

PASS = 0
FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
    extra = f" - {detail}" if detail else ""
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{extra}")


def kavippu_drills() -> None:
    print("\n=== Kavippu algorithm drills (Ch.1 Examples 1-3) ===")
    check("Aarudam 32 min -> Libra", get_aarudam(32) == "Libra")
    check("Aarudam 24 min -> Leo", get_aarudam(24) == "Leo")
    for label, aar, udh, sun, kav_exp in [
        ("Example 1", "Scorpio", "Leo", "Taurus", "Capricorn"),
        ("Example 2", "Scorpio", "Leo", "Virgo", "Aquarius"),
        ("Example 3", "Scorpio", "Leo", "Capricorn", "Pisces"),
    ]:
        k = get_kavippu(aar, udh, get_veedhi(sun))
        check(f"{label} Kavippu -> {kav_exp}", k["kavippu_sign"] == kav_exp, f"got {k['kavippu_sign']}")


def book_2019_manual_chart() -> None:
    """05/01/2019 11:49 a.m. Thanjavur  -  manual chart prep (pp.93-94)."""
    print("\n=== Dated chart JK-01: 05-01-2019 11:49 Thanjavur (manual prep) ===")
    check("Aarudam from minute 49 -> Capricorn", get_aarudam(49) == "Capricorn")
    check("Transit Sun Sagittarius -> Mithuna Veedhi", get_veedhi("Sagittarius") == "Mithuna")
    k = get_kavippu("Capricorn", "Pisces", get_veedhi("Sagittarius"))
    check("Kavippu -> Leo (book)", k["kavippu_sign"] == "Leo", f"got {k['kavippu_sign']}")
    check("Kavippu house 6 from Pisces Udhayam", k["kavippu_house_from_udhayam"] == 6)
    # Method 1 Udhayam arithmetic from book narrative
    udh = jamakkol_udhayam_method1(260.4833, 314)  # Sun 260d29m + 314min/2
    check("Method1 Udhayam longitude ~57 deg (Taurus band)", 50 < udh["udhayam_sidereal_deg"] < 65,
          f"{udh['udhayam_sidereal_deg']:.2f}")


def book_2003_case_chart() -> None:
    """11/09/2003 13:42 Thanjavur  -  case chart header (p.149)."""
    print("\n=== Dated chart JK-02: 11-09-2003 13:42 Thanjavur (case header) ===")
    check("Aarudam from minute 42 -> Sagittarius", get_aarudam(42) == "Sagittarius")
    data = precompute_horary("Who is my kula deiva?", "2003-09-11", "13:42", "Thanjavur")
    sun = data["planets"]["Sun"]["sign"]
    k = get_kavippu("Sagittarius", "Aries", get_veedhi(sun))
    check("Book Udhayam Mesha + ephemeris Sun -> Kavippu Simha", k["kavippu_sign"] == "Leo", f"got {k['kavippu_sign']}")
    check("Sun on date is Leo (supports Mesha Veedhi)", sun == "Leo")


def main() -> int:
    print("Jamakkol Prasanam book-example validation")
    kavippu_drills()
    book_2019_manual_chart()
    book_2003_case_chart()
    print(f"\n=== SUMMARY: {PASS} passed, {FAIL} failed ===")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
