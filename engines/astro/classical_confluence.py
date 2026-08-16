#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cross-method confluence for the Classical Vedic Report.

The repo already carries several complete prediction systems, each with its own
book corpus and its own way of reading a chart: Bhardwaj's case-book, Bhrigu
Nandi Nadi, Mehta's modern techniques, Jaimini's karakas, RTVD's year-wise
scan and the blind-chart progression. Until now the classical report answered
every question from Bhardwaj alone.

This module runs the others on the same chart and reports where they agree.
Nothing here quotes another lane's raw prose: the lanes write for an analyst,
and several of them make remarks about a spouse's looks that no customer should
read. What crosses over is the verdict each system reached, with the reason
stated in this report's own voice.

The heavyweight Bhardwaj semantic lane is deliberately not called — this report
has already built a `BhardwajChart`, so its column is read straight from the
chart for free, and the remaining lanes together cost about a second.
"""
from __future__ import annotations

from typing import Any, Optional

__all__ = ["AREAS", "METHOD_ORDER", "area_confluence", "confluence_rows"]

# state -> how it is counted and coloured
SUPPORT = "support"
CAUTION = "caution"
MIXED = "mixed"
# RTVD dates when an area comes forward; it does not judge the area good or
# bad, so its cell is counted as "this is live" rather than as an endorsement.
ACTIVE = "active"
QUIET = "quiet"

METHOD_ORDER = (
    "Bhardwaj case-book",
    "BNN nadi",
    "Mehta modern",
    "Jaimini karaka",
    "RTVD year-wise",
    "Blind chart",
)

#: key, label, house read for it, lane domains, RTVD topic, blind-chart title cue
AREAS: tuple[tuple[str, str, int, tuple[str, ...], str, str], ...] = (
    ("personality", "Personality", 1, ("personality",), "growth", "personality"),
    ("family", "Family", 4, ("property", "family"), "parents", "family"),
    ("career", "Career", 10, ("career",), "career", "career"),
    ("money", "Money", 2, ("finance",), "wealth", "wealth"),
    ("marriage", "Marriage", 7, ("marriage",), "marriage", "marriage"),
    ("children", "Children", 5, ("children",), "children", "children"),
    # Health is read from the ascendant, as the product's other lanes do; a
    # strong 6th lord means strong opposition, not a healthy body.
    ("health", "Health", 1, ("health",), "health", "health"),
)

BENEFIC = ("Jupiter", "Venus", "Mercury", "Moon")
MALEFIC = ("Saturn", "Mars", "Rahu", "Ketu", "Sun")
STRONG_DIGNITY = ("exalted", "own_sign", "moolatrikona")
WEAK_DIGNITY = ("debilitated", "enemy_sign")
GOOD_HOUSES = (1, 4, 5, 7, 9, 10, 11)
DUSTHANA = (6, 8, 12)


def _ord(n: int) -> str:
    n = int(n)
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}" + {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def _state(score: float) -> str:
    if score >= 0.5:
        return SUPPORT
    if score <= -0.5:
        return CAUTION
    return MIXED


# ---------------------------------------------------------------------------
# One column per method
# ---------------------------------------------------------------------------

def _bhardwaj_row(chart: Any, house: int) -> dict:
    """The case-book column, read from the chart this report already built."""
    lord = str((chart.houses.get(house) or {}).get("lord") or "")
    if not lord:
        return {"method": "Bhardwaj case-book", "state": QUIET, "note": ""}
    info = chart.planets.get(lord) or {}
    lord_in = int(info.get("house") or 0)
    dignity = str(info.get("dignity") or "")

    score = 0.0
    if dignity in STRONG_DIGNITY:
        score += 1
    elif dignity in WEAK_DIGNITY:
        score -= 1
    if lord_in in GOOD_HOUSES:
        score += 1
    elif lord_in in DUSTHANA:
        score -= 1
    tenants = [p for p in (chart.houses.get(house) or {}).get("tenants") or []]
    score += 0.5 * len([p for p in tenants if p in BENEFIC])
    score -= 0.5 * len([p for p in tenants if p in MALEFIC])

    note = f"your {_ord(house)} lord {lord} sits in the {_ord(lord_in)} house" \
        if lord_in else f"your {_ord(house)} lord is {lord}"
    if dignity in STRONG_DIGNITY or dignity in WEAK_DIGNITY:
        note += ", " + ("strong there" if dignity in STRONG_DIGNITY else "weak there")
    return {"method": "Bhardwaj case-book", "state": _state(score), "note": note}


def _lane_row(method: str, claims: list) -> dict:
    """A book lane's own balance over everything it said about the area."""
    if not claims:
        return {"method": method, "state": QUIET, "note": "no reading on this house"}
    positive = [c for c in claims if c.direction == "positive"]
    caution = [c for c in claims if c.direction == "caution"]
    if not positive and not caution:
        return {"method": method, "state": MIXED,
                "note": f"reads this house as workable rather than exceptional "
                        f"({len(claims)} reading{'s' if len(claims) > 1 else ''})"}
    balance = (len(positive) - len(caution)) / len(claims)
    read = f"{len(claims)} reading{'s' if len(claims) > 1 else ''} on this house"
    if positive and caution:
        read += f", {len(positive)} supportive and {len(caution)} cautionary"
    elif positive:
        read += ", leaning supportive"
    else:
        read += ", leaning cautionary"
    return {"method": method, "state": _state(balance * 2), "note": read}


def _rtvd_row(hits: list[dict]) -> dict:
    """RTVD does not judge an area; it dates when the area comes alive."""
    live = [h for h in hits if int(h.get("certainty") or 9) <= 2]
    if not live:
        return {"method": "RTVD year-wise", "state": QUIET,
                "note": "no clear year for this area in the twelve years scanned"}
    years = ", ".join(str(h.get("calendar")) for h in live[:3])
    return {"method": "RTVD year-wise", "state": ACTIVE,
            "note": f"marks {years} as the years this area comes forward"}


_BLIND_STATE = {"green": SUPPORT, "amber": CAUTION, "red": CAUTION}


def _blind_row(narratives: list[dict], cue: str) -> dict:
    """The progression reading, matched to its own section for this area."""
    for narrative in narratives or []:
        title = str(narrative.get("title") or "").lower()
        if cue in title or (cue == "money" and "wealth" in title):
            state = _BLIND_STATE.get(str(narrative.get("tone") or "").lower(), MIXED)
            return {"method": "Blind chart", "state": state,
                    "note": "the Jupiter and Saturn progression reads this area as "
                            + ("open" if state == SUPPORT else
                               "asking for care" if state == CAUTION else "steady")}
    return {"method": "Blind chart", "state": QUIET, "note": "no reading on this house"}


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def _lane_claims(pc: dict) -> dict[str, dict[str, list]]:
    """Claims from the fast book lanes, keyed lane -> domain -> [claim]."""
    out: dict[str, dict[str, list]] = {}
    name = str((pc.get("meta") or {}).get("client") or "")
    dob = str((pc.get("meta") or {}).get("dob") or "")
    if not name or not dob:
        return out
    import lane_collectors as LC
    for lane, collector in (("BNN nadi", "collect_bnn"),
                            ("Mehta modern", "collect_mehta"),
                            ("Jaimini karaka", "collect_jaimini")):
        try:
            claims = getattr(LC, collector)("", name, dob, pc)
        except Exception as exc:  # noqa: BLE001
            print(f"[classical_confluence] {lane} unavailable: {exc}", flush=True)
            continue
        for claim in claims:
            out.setdefault(lane, {}).setdefault(claim.domain, []).append(claim)
    return out


def _rtvd_hits(pc: dict) -> dict[str, list[dict]]:
    """RTVD's dated windows per topic, over the next twelve years."""
    try:
        from rtvd_year import topic_window_years
        from vedic_rtvd_report import RTVD
        rtvd = RTVD(pc)
        years = [rtvd.year(age) for age in range(rtvd.age, rtvd.age + 13)]
    except Exception as exc:  # noqa: BLE001
        print(f"[classical_confluence] RTVD unavailable: {exc}", flush=True)
        return {}
    hits: dict[str, list[dict]] = {}
    for _key, _label, _house, _domains, topic, _cue in AREAS:
        try:
            found = topic_window_years(rtvd, years, topic, rtvd.age, rtvd.age + 12)
        except Exception:  # noqa: BLE001
            found = []
        hits[topic] = sorted(found, key=lambda h: (h["certainty"], h["age"]))
    return hits


def _blind_narratives(pc: dict) -> list[dict]:
    try:
        from blind_chart_analysis import analyze_blind_chart
        return list((analyze_blind_chart(pc) or {}).get("narratives") or [])
    except Exception as exc:  # noqa: BLE001
        print(f"[classical_confluence] blind chart unavailable: {exc}", flush=True)
        return []


def area_confluence(rows: list[dict]) -> tuple[str, str]:
    """(agreement, direction) over the methods that actually spoke.

    Only support and caution are directional. A method that dates the area
    without judging it, or that reads the house as ordinary, counts as having
    spoken but does not pull the verdict either way.
    """
    heard = [r for r in rows if r["state"] != QUIET]
    if not heard:
        return "no reading", QUIET
    support = len([r for r in heard if r["state"] == SUPPORT])
    caution = len([r for r in heard if r["state"] == CAUTION])
    if not support and not caution:
        return "undecided", MIXED
    direction = SUPPORT if support > caution else CAUTION if caution > support else MIXED
    lead, against = max(support, caution), min(support, caution)
    if support and caution:
        agreement = "split" if lead - against <= 1 else "partial"
    elif lead >= 3:
        agreement = "strong"
    elif lead == 2:
        agreement = "partial"
    else:
        agreement = "thin"
    return agreement, direction


def confluence_rows(pc: dict, chart: Any) -> list[dict]:
    """One block per life area, with every method's verdict on it."""
    lanes = _lane_claims(pc)
    rtvd = _rtvd_hits(pc)
    blind = _blind_narratives(pc)

    blocks: list[dict] = []
    for key, label, house, domains, topic, cue in AREAS:
        rows = [_bhardwaj_row(chart, house)]
        for lane in ("BNN nadi", "Mehta modern", "Jaimini karaka"):
            claims: list = []
            for domain in domains:
                claims.extend((lanes.get(lane) or {}).get(domain) or [])
            rows.append(_lane_row(lane, claims))
        rows.append(_rtvd_row(rtvd.get(topic) or []))
        rows.append(_blind_row(blind, cue))

        agreement, direction = area_confluence(rows)
        blocks.append({
            "key": key, "label": label, "house": house, "rows": rows,
            "agreement": agreement, "direction": direction,
            "heard": len([r for r in rows if r["state"] != QUIET]),
            "support": len([r for r in rows if r["state"] == SUPPORT]),
            "caution": len([r for r in rows if r["state"] == CAUTION]),
        })
    return blocks


def method_note(rows: list[dict], method: str) -> Optional[str]:
    for row in rows:
        if row["method"] == method and row.get("note"):
            return str(row["note"])
    return None
