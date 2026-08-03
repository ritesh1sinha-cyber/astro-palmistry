#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Book-example validation for Vedic horary Python stack.

Run: python3 horary_book_examples_verify.py
"""
from __future__ import annotations

import sys

from horary_precompute import precompute_horary, julian_day, ist_to_ut
from kp_horary_engine import compute_kp_horary, kp_number_lookup

PASS = 0
FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    tag = "PASS" if ok else "FAIL"
    if ok:
        PASS += 1
    else:
        FAIL += 1
    extra = f" - {detail}" if detail else ""
    print(f"  {tag}  {name}{extra}")


def kp_arumugam_cure_example() -> None:
    print("\n=== KP Horary - Arumugam (2024) disease cure example ===")
    print("    13 Oct 2024 06:46 IST, Bangalore, KP# 30")

    jd = julian_day(2024, 10, 13, ist_to_ut(6, 46))
    lat, lon = 12.9716, 77.5946
    kp30 = kp_number_lookup(30)
    check("KP#30 canonical asc ~41.11 deg Taurus",
          abs(kp30["sidereal_asc_deg"] - 41.111111) < 0.01,
          f"{kp30['sidereal_asc_deg']:.4f}")

    pack = compute_kp_horary(30, jd, lat, lon, "disease_cure", 6)
    promise = pack["promise"]
    ca = pack["chart_a"]
    rp = pack["ruling_planets"]

    check("6th cusp sub-lord = Rahu", promise["cusp_sub_lord"] == "Rahu")
    check("Rahu (sub-lord) in house 11", promise["sub_lord_house"] == 11)
    check("Planet Rahu star-lord = Saturn", promise["star_lord"] == "Saturn")
    check("Star-lord signifies house 11 (cure)", 11 in promise["significations"])
    check("KP promise verdict = YES", promise["verdict"] == "YES")

    h5 = {"Sun", "Mercury", "Ketu"}
    h6 = {"Venus"}
    got5 = {p for p, h in ca["planet_houses"].items() if h == 5}
    got6 = {p for p, h in ca["planet_houses"].items() if h == 6}
    check("List A H5 occupants", got5 == h5, f"got {sorted(got5)}")
    check("List A H6 occupants", got6 == h6, f"got {sorted(got6)}")
    check("Rahu in H11", ca["planet_houses"].get("Rahu") == 11)

    lagna_rasi = set(rp["planets_in_lagna_rasi"])
    check("Chart B lagna rasi: Sun + Mercury",
          lagna_rasi >= {"Sun", "Mercury"}, f"got {sorted(lagna_rasi)}")

    book_rp = {"Venus", "Mars", "Mercury", "Saturn", "Jupiter", "Rahu", "Ketu"}
    got_rp = set(rp["all_ruling_planets"])
    check("Ruling Planets superset of book List B",
          book_rp <= got_rp, f"missing {book_rp - got_rp}")

    got_la = set(pack["list_a"])
    check("List A significators exact", got_la == {"Sun", "Mercury", "Ketu", "Venus", "Mars", "Jupiter", "Saturn", "Rahu"},
          f"got {sorted(got_la)}")

    book_lc = {"Mercury", "Ketu", "Venus", "Mars", "Jupiter", "Saturn", "Rahu"}
    got_lc = set(pack["list_c"])
    expected_lc = got_la & got_rp
    check("List C = List A cap Ruling Planets",
          got_lc == expected_lc, f"got {sorted(got_lc)} expected {sorted(expected_lc)}")
    check("List C contains book members (day lord Sun may be extra per KSK)",
          book_lc <= got_lc, f"got {sorted(got_lc)}")

    data = precompute_horary(
        "When will I be cured of the disease?", "2024-10-13", "06:46", "Bangalore", "30"
    )
    check("Topic detected disease_cure", data["meta"]["detected_topic"] == "disease_cure")
    check("precompute promise YES", data["kp_data"]["promise"]["verdict"] == "YES")


def main() -> int:
    print("Vedic horary book-example validation")
    jamakkol_rc = 0
    try:
        from jamakkol_book_examples_verify import main as jamakkol_main
        jamakkol_rc = jamakkol_main()
    except Exception as exc:
        print(f"\n=== Jamakkol validation ERROR: {exc} ===")
        jamakkol_rc = 1
    kp_arumugam_cure_example()
    try:
        from prashna_book_examples_verify import main as prashna_main
        prashna_rc = prashna_main()
    except Exception as exc:
        print(f"\n=== Prashna validation ERROR: {exc} ===")
        prashna_rc = 1
    print(f"\n=== OVERALL: KP {PASS} passed, {FAIL} failed; Jamakkol rc={jamakkol_rc}; Prashna rc={prashna_rc} ===")
    return 0 if FAIL == 0 and prashna_rc == 0 and jamakkol_rc == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
