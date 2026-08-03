#!/usr/bin/env python3
"""
Sanity check: Arumugam (2024) KP Horary worked example vs production engine.

Book: 13 Oct 2024, 06:46 IST (= 01:16 UT), Bangalore, KP horary number 30.

Run: python3 kp_horary_book_example_verify.py
"""
from __future__ import annotations

from horary_precompute import julian_day, ist_to_ut
from kp_horary_engine import compute_kp_horary, kp_number_lookup

BOOK_H5 = {"Sun", "Mercury", "Ketu"}
BOOK_H6 = {"Venus"}
BOOK_LIST_A = {"Sun", "Mercury", "Ketu", "Venus", "Mars", "Jupiter", "Saturn", "Rahu"}
BOOK_LIST_C = {"Mercury", "Ketu", "Venus", "Mars", "Jupiter", "Saturn", "Rahu", "Sun"}
BOOK_LAGNA_RASI = {"Sun", "Mercury"}


def main() -> None:
    jd = julian_day(2024, 10, 13, ist_to_ut(6, 46))
    lat, lon = 12.9716, 77.5946
    kp_num = 30

    pack = compute_kp_horary(kp_num, jd, lat, lon, "disease_cure", 6)
    kp = kp_number_lookup(kp_num)
    ca = pack["chart_a"]
    promise = pack["promise"]
    rp = pack["ruling_planets"]

    print("=== KP Horary book example (production engine) ===")
    print(f"Instant: JD {jd:.6f} UT, Bangalore, KP# {kp_num}\n")

    print(f"KP#30 sidereal ASC: {kp['sidereal_asc_deg']:.4f} deg ({kp['sign']})")
    print(f"6th cusp sub-lord: {promise['cusp_sub_lord']} (book: Rahu)")
    print(f"Sub-lord {promise['sub_lord_planet']} in house {promise['sub_lord_house']} (book: Rahu in 11)")
    print(f"Star-lord: {promise['star_lord']} (book: Saturn)")
    print(f"Significations: {promise['significations']} (book includes 11)")
    print(f"Promise: {promise['verdict']} - {promise['reason']}\n")

    got5 = {p for p, h in ca["planet_houses"].items() if h == 5}
    got6 = {p for p, h in ca["planet_houses"].items() if h == 6}
    print(f"List A H5 occupants {got5} vs book {BOOK_H5} -> {got5 == BOOK_H5}")
    print(f"List A H6 occupants {got6} vs book {BOOK_H6} -> {got6 == BOOK_H6}")
    print(f"Chart B lagna rasi {set(rp['planets_in_lagna_rasi'])} vs book {BOOK_LAGNA_RASI}")
    got_la = set(pack["list_a"])
    got_lc = set(pack["list_c"])
    print(f"List A significators {got_la} vs book {BOOK_LIST_A} -> {got_la == BOOK_LIST_A}")
    print(f"List C {got_lc} vs book {BOOK_LIST_C} -> {got_lc == BOOK_LIST_C}")

    ok = (
        promise["cusp_sub_lord"] == "Rahu"
        and promise["sub_lord_house"] == 11
        and promise["star_lord"] == "Saturn"
        and 11 in promise["significations"]
        and promise["verdict"] == "YES"
        and got5 == BOOK_H5
        and got6 == BOOK_H6
        and got_la == BOOK_LIST_A
        and got_lc == BOOK_LIST_C
        and BOOK_LAGNA_RASI <= set(rp["planets_in_lagna_rasi"])
        and got_lc == (got_la & set(rp["all_ruling_planets"]))
    )
    print(f"\nOVERALL: {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
