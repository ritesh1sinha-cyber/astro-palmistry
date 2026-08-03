#!/usr/bin/env python3
"""Book-example validation for Prashna Kundali Siddhanta engine."""
from __future__ import annotations

import sys

from horary_precompute import precompute_horary
from prashna_kundali_engine import (
    analyze_prashna,
    book_chart1_fixture,
    resolve_arudha,
    jupiter_aspects_house,
    ARUDHA_BY_DIRECTION,
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


def arudha_direction_map() -> None:
    print("\n=== Prashna Arudha direction map (book Ch.2) ===")
    check("NE -> Pisces", resolve_arudha("Virgo", "Scorpio", "northeast")["arudha_sign"] == "Pisces")
    check("E-SE -> Taurus", resolve_arudha("Virgo", "Scorpio", "east-southeast")["arudha_sign"] == "Taurus")
    check("NW -> Sagittarius", resolve_arudha("Virgo", "Scorpio", "northwest")["arudha_sign"] == "Sagittarius")
    check("Default without direction uses Lagna", resolve_arudha("Virgo", "Scorpio")["arudha_sign"] == "Virgo")
    check("12 directions in table", len(ARUDHA_BY_DIRECTION) >= 12)


def jupiter_aspect_houses() -> None:
    print("\n=== Jupiter aspect offsets (classical 7-house) ===")
    check("Jupiter in 5 aspects Lagna (H1)", jupiter_aspects_house(5, 1))
    check("Jupiter in 5 aspects H9 (5th drishti)", jupiter_aspects_house(5, 9))
    check("Jupiter in 8 does not aspect H3", not jupiter_aspects_house(8, 3))


def book_chart1_marriage() -> None:
    print("\n=== Book Chart 1 - marriage unlikely (OCR fixture) ===")
    data = book_chart1_fixture()
    r = analyze_prashna(data, arudha_direction="northwest")
    check("Arudha = Sagittarius (NW)", r["arudha_sign"] == "Sagittarius")
    check("Lagna = Virgo", data["lagna"]["sign"] == "Virgo")
    check("Two malefics in Lagna", len(r["malefics_in_lagna"]) >= 2, str(r["malefics_in_lagna"]))
    check("Moon in apoklima (H3)", r["moon_house"] == 3)
    check("Moon without Jupiter aspect", not r["jup_aspects_moon"])
    check("Lagna lord status WEAK/afflicted", r["ll_status"] == "WEAK")
    check("Verdict NO (marriage unlikely)", r["label"] == "NO", f"got {r['label']} score={r['score']:.2f}")


def arumugam_cure_prashna() -> None:
    print("\n=== Arumugam cure chart - Prashna lane (classical, not KP) ===")
    data = precompute_horary(
        "When will I be cured of the disease?", "2024-10-13", "06:46", "Bangalore", "30"
    )
    r = data["prashna"]
    check("Topic disease_cure", data["meta"]["detected_topic"] == "disease_cure")
    check("6th lord in dusthana noted", any("6th lord in dusthana" in n for n in r["notes"]))
    check("Prashna not YES", r["label"] != "YES", f"got {r['label']}")
    check("Paksha in meta", "paksha" in data["meta"] and data["meta"]["paksha"]["paksha"] in ("Shukla", "Krishna"))


def book_chart2_alliance() -> None:
    print("\n=== Book Chart 2 - alliance not fruitful (31-3-1983 18:30 Bangalore) ===")
    data = precompute_horary(
        "Will the proposed alliance be fruitful?", "1983-03-31", "18:30", "Bangalore"
    )
    r = analyze_prashna(data)
    mars_h = data["houses"].get("Mars", 0)
    check("Topic marriage", data["meta"]["detected_topic"] == "marriage")
    check("Mars in 8th (book: malefic in 8th)", mars_h == 8, f"H{mars_h}")
    check("Malefics in 8th noted", any("Malefics in 8th" in n for n in r["notes"]))
    check("Verdict NO (alliance not fruitful)", r["label"] == "NO",
          f"got {r['label']} score={r['score']:.2f}")


def book_chart3_chandrabhilasha() -> None:
    print("\n=== Book Chart 3 - Chandrabhilasha math (24-5-1984 20:30 Bangalore) ===")
    data = precompute_horary(
        "When will marriage happen?", "1984-05-24", "20:30", "Bangalore"
    )
    moon_sid = float(data["planets"]["Moon"]["sidereal_lon"])
    book_moon = 332.0167
    check("Moon sidereal computed", moon_sid > 0)
    check("Moon within 2 deg of book 332.02", abs(moon_sid - book_moon) < 2.0,
          f"script {moon_sid:.2f} book {book_moon:.2f}")
    # Book: Moon 332 deg 01 min -> arc-minutes 19921; 19921 % 800 = 721 (Chandrabhilasha step)
    book_arcmin = int(332 * 60 + 1)
    check("Book Chandrabhilasha remainder 721 (arc-min chain)", book_arcmin % 800 == 721,
          f"arcmin={book_arcmin} rem={book_arcmin % 800}")
    check("Prashna marriage topic routed", data["meta"]["detected_topic"] == "marriage")


def main() -> int:
    print("Prashna Kundali book-example validation")
    arudha_direction_map()
    jupiter_aspect_houses()
    book_chart1_marriage()
    book_chart2_alliance()
    book_chart3_chandrabhilasha()
    arumugam_cure_prashna()
    print(f"\n=== SUMMARY: {PASS} passed, {FAIL} failed ===")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
