#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Anchor planet (line main) + sub-planet house readings.

If Jupiter is in the 8th, Jupiter is the line-lord for the 8th-house palm zone.
Every other planet in its house is a sub-planet with its own palm mark. The
confluence merges themes across anchors and sub-planets.

WHY THIS FILE WAS REWRITTEN
---------------------------
The first version keyed its readings off hand-written `MAIN_LINE` and
`SUB_PLANET` tables of (planet, house) pairs. Those nine pairs were exactly one
test subject's nine placements, which was measurable and bad:

    that chart:        MAIN_LINE fired 9/9   (100%)
    12 random charts:  MAIN_LINE fired 5/108 (5%)

So 95% of real readers got generic fallback prose, and the 5% who did hit an
entry could be told things about their chart that were false, because the
entry's text asserted the ORIGINAL chart's facts. Measured on the same 12
charts, two such assertions landed in a single reading:

    "Mars in 11th with moolatrikona"  -> that Mars was in a neutral sign
    "Rahu co-tenant amplifies..."     -> that Rahu was in the 6th, not the 11th

A table cannot know a stranger's dignities or co-tenants, so it must not claim
them. Everything is now COMPOSED per chart from three layers that are true for
everybody:

    1. PLANET_MOUNT  planet -> its mount on the palm      (classical palmistry)
    2. HOUSE_ZONE    house  -> theme + the lines that carry it   (both systems)
    3. DIGNITY       dignity -> tone and strength wording        (Jyotish)

Relationships between an anchor and a sub-planet are likewise DERIVED from the
two actual placements (conjunction, opposition, trine, dusthana-from-anchor)
rather than looked up, so they are true by construction.

Longevity is deliberately absent. The 8th house is read as a health-and-upheaval
zone, and `no_longevity.scrub()` is the final gate on every string this module
emits, so no lifespan language can survive even if a caller adds some.
"""
from __future__ import annotations

from typing import Any

from astro_palmistry_zone_cv import DOMAIN_ZONES as _CV_DOMAIN_ZONES
from astro_palmistry_zone_cv import cv_finding_sentence


def _ord(n: Any) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n)
    return f"{n}" + ("th" if 10 <= n % 100 <= 20
                     else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


# The CV module keeps a "longevity" domain whose zones (h8, life line) are the
# right places to LOOK for 8th-house material. We still inspect them — we just
# report them as health and upheaval. Folding them into health here means the
# zones are not orphaned now that the longevity domain is never emitted.
DOMAIN_ZONES: dict[str, list[str]] = {
    d: list(z) for d, z in _CV_DOMAIN_ZONES.items() if d != "longevity"
}
DOMAIN_ZONES["health"] = list(dict.fromkeys(
    DOMAIN_ZONES.get("health", []) + _CV_DOMAIN_ZONES.get("longevity", [])))

try:
    from no_longevity import scrub as _scrub
except Exception:                                                    # noqa: BLE001
    def _scrub(text: Any) -> str:                                    # type: ignore
        return str(text or "")

PLANET_ZONE: dict[str, str] = {
    "Sun": "sun",
    "Moon": "moon",
    "Mars": "mars",
    "Mercury": "mercury",
    "Jupiter": "jupiter",
    "Venus": "venus",
    "Saturn": "saturn",
    "Rahu": "rahu",
    "Ketu": "ketu",
}

HOUSE_THEMES: dict[int, str] = {
    1: "self, body, vitality",
    2: "wealth, family, speech",
    3: "siblings, courage, documents",
    4: "mother, home, property",
    5: "children, romance, creativity",
    6: "health, service, debts",
    7: "marriage, partnership",
    # Never "longevity". The 8th is read as upheaval and inherited matters;
    # lifespan is out of scope for this product by policy, and no_longevity
    # scrubs the output as a backstop.
    8: "upheaval, inheritance, sudden turns",
    9: "luck, father-guru, dharma",
    10: "career, status, authority",
    11: "gains, friends, fulfilment",
    12: "expenses, foreign lands, private strain",
}

# ---------------------------------------------------------------------------
# Layer 1 — planet to mount. Classical palmistry, identical for every hand.
# ---------------------------------------------------------------------------
PLANET_MOUNT: dict[str, tuple[str, str]] = {
    "Sun": ("mount of the Sun, under the ring finger",
            "recognition and the work being seen"),
    "Moon": ("mount of the Moon at the percussion",
             "imagination, moods and travel"),
    "Mars": ("plain and mounts of Mars, either side of the palm",
             "courage, resistance and appetite for a fight"),
    "Mercury": ("mount of Mercury, under the little finger",
                "speech, negotiation and commerce"),
    "Jupiter": ("mount of Jupiter, under the index finger",
                "authority, ambition and belief"),
    "Venus": ("mount of Venus, the ball of the thumb",
              "affection, vitality and pleasure"),
    "Saturn": ("mount of Saturn, under the middle finger",
               "discipline, solitude and endurance"),
    "Rahu": ("zone above the heart line",
             "hunger for what is out of reach"),
    "Ketu": ("lower percussion below the Moon mount",
             "detachment and what is being let go"),
}

# ---------------------------------------------------------------------------
# Layer 2 — house to the palm lines that carry it, plus the life question it
# asks. General to any chart.
# ---------------------------------------------------------------------------
HOUSE_ZONE: dict[int, tuple[str, str]] = {
    1: ("the life line where it leaves the thumb", "how much stamina you start with"),
    2: ("the head line's early third and the Mercury mount",
        "what you earn and what you say"),
    3: ("the short branches rising off the life line",
        "nerve, siblings and paperwork"),
    4: ("the base of the fate line and the Moon mount",
        "home, mother and the roof over you"),
    5: ("the fine lines under the heart line toward Venus",
        "children, romance and what you make"),
    6: ("the health line and the barred part of the Saturn mount",
        "illness, service and who opposes you"),
    7: ("the marriage lines on the percussion below the little finger",
        "partnership and who you bind yourself to"),
    8: ("crossings on the life and fate lines",
        "upheaval, inherited matters and what arrives without warning"),
    9: ("the intuition line and the travel lines toward the Moon mount",
        "luck, teachers and long journeys"),
    10: ("the fate line where it climbs to the Saturn mount",
         "career and public standing"),
    11: ("the branches rising to the Jupiter and Sun mounts",
         "gains, friends and desires actually met"),
    12: ("the faint lines toward the wrist and under the Moon mount",
         "expense, foreign ground and private strain"),
}

# House to the confluence domain. 8 maps to health, not longevity.
HOUSE_DOMAIN: dict[int, str] = {
    1: "health", 2: "gains", 3: "gains", 4: "home", 5: "children",
    6: "health", 7: "home", 8: "health", 9: "luck", 10: "career",
    11: "gains", 12: "health",
}

# ---------------------------------------------------------------------------
# Layer 3 — dignity to tone and to how the mount should read.
# ---------------------------------------------------------------------------
DIGNITY: dict[str, tuple[str, str, str]] = {
    # dignity -> (tone, strength phrase, expected mount appearance)
    "exalted": ("support", "at its strongest",
                "full and clearly formed"),
    "moolatrikona": ("support", "on comfortable ground",
                     "well shaped and firm"),
    "own_sign": ("support", "in its own sign",
                 "clean and well defined"),
    "friendly_sign": ("mixed", "reasonably placed",
                      "adequately formed"),
    "neutral_sign": ("mixed", "neither helped nor hindered",
                     "ordinary, neither full nor flat"),
    "enemy_sign": ("caution", "on difficult ground",
                   "flat or crossed"),
    "debilitated": ("caution", "at its weakest",
                    "flat, or cut by fine cross-lines"),
}
DUSTHANA = (6, 8, 12)

TONE_SCORE = {"support": 2, "mixed": 0, "caution": -2}

# Kept for backward compatibility with callers that imported these names. They
# are intentionally empty: a lookup table of (planet, house) prose cannot know a
# stranger's dignities or co-tenants, which is how the old version put false
# statements into real readings. `palm_astro_bridge` imports PLANET_ZONE only.
MAIN_LINE: dict[tuple[str, int], dict[str, str]] = {}
SUB_PLANET: dict[tuple[str, int], dict[str, str]] = {}
RELATIVE_SUB: dict[tuple[str, int], list[tuple[tuple[str, int], str]]] = {}


def _tone(dignity: str, house: int) -> str:
    """Dignity sets the tone; a dusthana house pulls a neutral one down."""
    tone = DIGNITY.get(dignity, ("mixed", "", ""))[0]
    if house in DUSTHANA and tone == "mixed":
        return "caution"
    return tone


def _reading(planet: str, house: int, dignity: str, sign: str,
             *, role: str) -> dict[str, str]:
    """Compose one placement's palm zone and life reading from the chart.

    Every clause is derived from the four arguments, so nothing can be asserted
    that this chart does not contain. That is the whole point of the rewrite.
    """
    mount, mount_gov = PLANET_MOUNT.get(
        planet, ("plain of Mars", "drive and resistance"))
    lines, question = HOUSE_ZONE.get(
        house, ("the fate line", HOUSE_THEMES.get(house, "this area of life")))
    tone, strength, appearance = DIGNITY.get(
        dignity, ("mixed", "placed without strong help or harm",
                  "ordinary in form"))
    theme = HOUSE_THEMES.get(house, "this area of life")

    if role == "main":
        palm = (f"{planet} is the line-lord here, so read the {mount} together "
                f"with {lines}. In a chart like yours that mount should look "
                f"{appearance}.")
    else:
        palm = (f"Read the {mount} against {lines} — {appearance} is what this "
                f"placement predicts.")

    hard = house in DUSTHANA
    # "shows up in" rather than "is working through": mount_gov is a list of
    # nouns ("authority, ambition and belief"), so a copula forces a
    # subject-verb agreement error that no table edit can fix.
    life = (f"{planet} sits in your {_ord(house)} house in {sign}, "
            f"{strength}. That house governs {theme}, so {mount_gov} shows up "
            f"in {question}.")
    if tone == "caution" and hard:
        life += (" A difficult house and a weak placement together: expect "
                 "this area to ask for effort rather than hand anything over.")
    elif tone == "caution":
        life += (" The placement is under strain, so progress here is earned "
                 "rather than given.")
    elif tone == "support" and hard:
        life += (" A strong planet in a hard house — the difficulty is real "
                 "but you are equipped for it.")
    elif tone == "support":
        life += " This is one of the better-supported parts of your chart."

    return {"palm": palm, "life": life,
            "domain": HOUSE_DOMAIN.get(house, "health"), "tone": tone}


def _ord(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def _relation(a_planet: str, a_house: int, s_planet: str, s_house: int,
              s_dignity: str) -> str:
    """Derive the anchor/sub relationship from the two real placements.

    Replaces a lookup table whose entries described one specific chart. Because
    this is computed, it is true for whatever chart it is handed.
    """
    if a_house == s_house:
        return (f"{s_planet} shares the {_ord(a_house)} house with {a_planet}, "
                f"so both read on the same palm zone and their themes arrive "
                f"together rather than separately.")
    gap = (s_house - a_house) % 12
    if gap == 6:
        return (f"{s_planet} sits opposite {a_planet}, {_ord(s_house)} against "
                f"{_ord(a_house)} — the two pull against each other, and the "
                f"palm usually shows one zone fuller than the other.")
    if gap in (4, 8):
        return (f"{s_planet} makes a supporting trine to {a_planet} from the "
                f"{_ord(s_house)}, so it eases what {a_planet} is carrying.")
    if gap in (2, 10):
        return (f"{s_planet} in the {_ord(s_house)} works quietly alongside "
                f"{a_planet}, close enough to help but not to dominate.")
    if s_house in DUSTHANA:
        extra = " and weakly placed" if s_dignity in (
            "debilitated", "enemy_sign") else ""
        return (f"{s_planet} lies in the {_ord(s_house)}, a difficult house{extra}, "
                f"so it complicates rather than supports {a_planet}'s area.")
    return (f"{s_planet} in the {_ord(s_house)} is largely independent of "
            f"{a_planet} — read its own mount on its own terms.")

def build_anchor_analysis(planets: dict[str, dict], lagna: str) -> dict[str, Any]:
    plist = sorted(
        [(p, d) for p, d in planets.items()],
        key=lambda x: (-1 if x[1].get("dignity") == "debilitated" else 0, x[1].get("house", 99)),
    )

    anchors: list[dict[str, Any]] = []
    for planet, info in plist:
        h = int(info["house"])
        main = _reading(planet, h, info["dignity"], info["sign"], role="main")
        subs: list[dict[str, Any]] = []
        for sp, si in plist:
            if sp == planet:
                continue
            sh = int(si["house"])
            sub = _reading(sp, sh, si["dignity"], si["sign"], role="sub")
            subs.append({
                "planet": sp,
                "sign": si["sign"],
                "house": sh,
                "dignity": si["dignity"],
                "zone_id": PLANET_ZONE.get(sp, "mars"),
                "palm": _scrub(sub["palm"]),
                "life": _scrub(sub["life"]),
                "domain": sub["domain"],
                "tone": sub["tone"],
                # Derived from the two real placements, so it cannot describe
                # some other chart's geometry.
                "relative_to_anchor": _scrub(
                    _relation(planet, h, sp, sh, si["dignity"])),
            })
        anchors.append({
            "planet": planet,
            "sign": info["sign"],
            "house": h,
            "dignity": info["dignity"],
            "zone_id": PLANET_ZONE.get(planet, "mars"),
            "role": "line_main",
            "palm": _scrub(main["palm"]),
            "life": _scrub(main["life"]),
            "domain": main["domain"],
            "tone": main["tone"],
            "sub_planets": subs,
        })

    zone_plan: list[dict[str, str]] = []
    seen: set[str] = set()
    for a in anchors:
        z = a["zone_id"]
        if z not in seen:
            zone_plan.append({"planet": a["planet"], "zone_id": z, "label": f"{a['planet']}@{a['house']} main", "role": "main"})
            seen.add(z)
        for s in a["sub_planets"]:
            z2 = s["zone_id"]
            if z2 not in seen:
                zone_plan.append({"planet": s["planet"], "zone_id": z2, "label": f"{s['planet']}@{s['house']} sub", "role": "sub"})
                seen.add(z2)

    return {"lagna": lagna, "anchors": anchors, "confluence": [], "zone_plan": zone_plan}


def apply_cv_evidence(analysis: dict[str, Any], zone_metrics: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """
    Attach CV findings to anchors and rebuild confluence from actual print inspection.
    No duplicate notes; says 'photo not clear' when zone unreadable.
    """
    has_photos = bool(zone_metrics)
    anchors = analysis.get("anchors", [])

    for a in anchors:
        zid = a["zone_id"]
        stress = a.get("tone") == "caution"
        a["cv_finding"] = cv_finding_sentence(zid, zone_metrics.get(zid, {}), stress) if has_photos else "No palm photo supplied."
        for s in a.get("sub_planets", []):
            sz = s["zone_id"]
            s["cv_finding"] = cv_finding_sentence(sz, zone_metrics.get(sz, {}), s.get("tone") == "caution") if has_photos else "No palm photo supplied."

    # Cross-link each anchor to the most significant OTHER placement in its own
    # domain. The old version hardcoded Ketu@5 against Jupiter@8 — the two
    # placements belonging to the chart this file was written against, so the
    # link appeared for one person and for nobody else.
    for a in anchors:
        best: tuple[int, str, str] = (-1, "", "")
        for other in anchors:
            if other is a or other["domain"] != a["domain"]:
                continue
            # Prefer a conjunction, then an opposition, then anything strong.
            gap = (other["house"] - a["house"]) % 12
            weight = 3 if gap == 0 else (2 if gap == 6 else 1)
            if other["tone"] == "caution":
                weight += 1
            if weight > best[0]:
                best = (weight, other["planet"],
                        _relation(a["planet"], a["house"], other["planet"],
                                  other["house"], other["dignity"]))
        if best[0] > 0:
            a["chart_link"] = _scrub(best[2])
            a["chart_link_with"] = f"{best[1]}@{next(o['house'] for o in anchors if o['planet'] == best[1])}"

    # One note per planet@house per domain (deduped)
    domain_entries: dict[str, dict[tuple[str, int, str], str]] = {}

    def _add(dom: str, planet: str, house: int, role: str, text: str) -> None:
        key = (planet, house, role)
        if key not in domain_entries.setdefault(dom, {}):
            domain_entries[dom][key] = text

    anchor_keys = {(a["planet"], a["house"]) for a in anchors}

    for a in anchors:
        dom = a["domain"]
        _add(dom, a["planet"], a["house"], "chart", f"{a['planet']}@{a['house']} (chart): {a['life'][:100]}")
        if a.get("chart_link"):
            vs = a.get("chart_link_with", "chart")
            _add(dom, a["planet"], a["house"], "link",
                 f"{a['planet']}@{a['house']} (vs {vs}): {a['chart_link'][:120]}")
        _add(dom, a["planet"], a["house"], "print", f"{a['planet']}@{a['house']} (print): {a['cv_finding']}")
        for s in a.get("sub_planets", []):
            sd = s["domain"]
            sk = (s["planet"], s["house"])
            _add(sd, s["planet"], s["house"], "print", f"{s['planet']}@{s['house']} (print): {s['cv_finding']}")
            if sk in anchor_keys:
                continue
            rel = s.get("relative_to_anchor", "")
            chart_line = f"{s['planet']}@{s['house']} (chart): {s['life'][:90]}"
            if rel:
                chart_line += f" Vs {a['planet']}@{a['house']}: {rel[:90]}"
            _add(sd, s["planet"], s["house"], "chart", chart_line)

    confluence: list[dict[str, Any]] = []
    for dom in sorted(domain_entries.keys()):
        entries = domain_entries[dom]
        relevant_zones = DOMAIN_ZONES.get(dom, [])
        zone_hits = {z: zone_metrics[z] for z in relevant_zones if z in zone_metrics}

        chart_score = sum(
            TONE_SCORE.get(a["tone"], 0) for a in anchors if a["domain"] == dom
        ) + sum(
            TONE_SCORE.get(s["tone"], 0) for a in anchors for s in a.get("sub_planets", []) if s["domain"] == dom
        )

        notes = list(entries.values())
        for z in relevant_zones:
            if z in zone_metrics:
                if any(f"{z} zone" in n or f"in {z} zone" in n for n in notes):
                    continue
                zm = zone_metrics[z]
                zline = f"{z} zone (print): {cv_finding_sentence(z, zm, chart_score <= 0)}"
                notes.append(zline)
        notes = notes[:10]

        unclear = [z for z, m in zone_hits.items() if not m.get("readable")]
        stress_confirmed = [z for z, m in zone_hits.items() if m.get("readable") and m.get("stress_lines")]
        sparse = [z for z, m in zone_hits.items() if m.get("readable") and m.get("sparse")]

        if not has_photos:
            verdict, conf = "Chart-only read (no palm photo analysed).", "chart-only"
        elif len(unclear) == len(relevant_zones) and relevant_zones:
            verdict = (
                f"Photo not clear for {dom} zones ({', '.join(unclear)}) - "
                f"cannot confirm lines on this print. Re-upload close-ups."
            )
            conf = "low"
        elif unclear:
            verdict = (
                f"Partially unreadable: {', '.join(unclear)} blurry on print. "
                f"Readable zones: {', '.join(z for z in zone_hits if z not in unclear) or 'none'}."
            )
            conf = "moderate"
        elif stress_confirmed and chart_score < 0:
            verdict = (
                f"Chart stress for {dom} is visible on your print - dense lines in "
                f"{', '.join(stress_confirmed)} zone(s)."
            )
            conf = "moderate-high"
        elif stress_confirmed and chart_score == 0:
            # A score of zero means the methods came out NEUTRAL, not stressed.
            # The old branch used `<= 0`, so it reported "chart stress" for every
            # merely-mixed area — a warning the chart never actually gave.
            verdict = (
                f"Your chart is neutral on {dom}, but the print shows dense lines "
                f"in {', '.join(stress_confirmed)} - worth watching rather than "
                f"worrying about."
            )
            conf = "moderate"
        elif sparse and chart_score < 0:
            verdict = (
                f"Chart flags {dom} stress but print shows sparse lines in "
                f"{', '.join(sparse)} - pattern not heavy on this photo."
            )
            conf = "moderate"
        elif chart_score >= 2:
            verdict = f"Chart and print both lean favourable for {dom}."
            conf = "moderate-high"
        else:
            verdict = f"Mixed {dom} pattern between chart and print."
            conf = "moderate"

        confluence.append({
            "domain": dom,
            "verdict": verdict,
            "confidence": conf,
            "notes": notes,
        })

    analysis["anchors"] = anchors
    analysis["confluence"] = confluence
    analysis["zone_metrics"] = zone_metrics
    analysis["cv_inspected"] = has_photos
    return analysis


DOMAIN_TITLES: dict[str, str] = {
    "career": "Career & public standing",
    "children": "Children & creativity",
    "gains": "Gains, friends & fulfilment",
    "health": "Health, service & stamina",
    "home": "Home, mother & property",
    "luck": "Luck, travel & dharma",
}

CONFIDENCE_PHRASE: dict[str, str] = {
    "moderate-high": "Fairly confident",
    "moderate": "Moderate confidence",
    "low": "Low confidence",
    "chart-only": "Chart only (no palm photo)",
}


def _chart_lines_for_domain(anchors: list[dict], domain: str) -> list[str]:
    lines: list[str] = []
    seen: set[tuple[str, int]] = set()
    for a in anchors:
        if a.get("domain") != domain:
            for s in a.get("sub_planets", []):
                if s.get("domain") == domain:
                    k = (s["planet"], s["house"])
                    if k not in seen:
                        seen.add(k)
                        lines.append(f"{s['planet']} in the {_ord(s['house'])} ({s['sign']}) - {s['life']}")
            continue
        k = (a["planet"], a["house"])
        if k not in seen:
            seen.add(k)
            lines.append(f"{a['planet']} in the {_ord(a['house'])} ({a['sign']}) - {a['life']}")
        for s in a.get("sub_planets", []):
            if s.get("domain") == domain:
                sk = (s["planet"], s["house"])
                if sk not in seen:
                    seen.add(sk)
                    rel = s.get("relative_to_anchor") or ""
                    extra = f" This links to {a['planet']} in the {_ord(a['house'])} house: {rel}" if rel else ""
                    lines.append(f"{s['planet']} in the {_ord(s['house'])} ({s['sign']}) - {s['life']}{extra}")
    return lines[:4]


def _print_lines_for_domain(
    zone_metrics: dict[str, dict],
    zones: list[str],
) -> tuple[list[str], list[str]]:
    """Return (readable sentences, unclear zone names)."""
    readable: list[str] = []
    unclear: list[str] = []
    for z in zones:
        m = zone_metrics.get(z)
        if not m:
            continue
        if not m.get("readable"):
            unclear.append(z)
            continue
        lc = m.get("line_count", 0)
        sharp = m.get("sharpness", 0)
        q = m.get("quality", "fair")
        if m.get("stress_lines"):
            readable.append(
                f"On your print the {z} zone shows {lc} vertical lines (sharpness {sharp}, {q}) - "
                f"a dense cross-line pattern in an area the chart flags as stressed."
            )
        elif m.get("sparse"):
            readable.append(
                f"On your print the {z} zone shows only {lc} line(s) (sharpness {sharp}) - "
                f"sparse marking; the chart's stress is not mirrored as a heavy grille here."
            )
        else:
            readable.append(
                f"On your print the {z} zone shows {lc} vertical lines (sharpness {sharp}, {q} quality)."
            )
    return readable, unclear


def _human_verdict_rewrite(domain: str, verdict: str, unclear: list[str], readable: list[str]) -> str:
    """Turn machine verdict into one plain sentence."""
    title = DOMAIN_TITLES.get(domain, domain)
    if "Photo not clear for" in verdict or "cannot confirm" in verdict:
        return f"Your {title.lower()} chapter cannot be verified from this palm photo - key zones were too blurry."
    if unclear and readable:
        return (
            f"Your {title.lower()} picture is only partly visible on the print: "
            f"we could read the {', '.join(readable)} area(s), but {', '.join(unclear)} need close-up photos."
        )
    if "dense lines" in verdict or "visible on your print" in verdict:
        return f"Chart stress for {title.lower()} shows on the palm as dense cross-lines in the zones we could read."
    if "sparse lines" in verdict:
        return f"The chart flags {title.lower()} pressure, but the palm photo shows lighter marking than expected."
    if "lean favourable" in verdict:
        return f"Both chart and palm lean supportive for {title.lower()}."
    if "Chart-only" in verdict:
        return f"{title} is read from the birth chart only - no palm photo was checked."
    return verdict.replace("Partially unreadable:", "Partly unreadable on photo:").replace(" blurry on print", " too blurry")


def _human_domain_paragraph(
    domain: str,
    verdict: str,
    confidence: str,
    anchors: list[dict],
    zone_metrics: dict[str, dict],
) -> str:
    title = DOMAIN_TITLES.get(domain, domain.title())
    conf = CONFIDENCE_PHRASE.get(confidence, confidence)
    zones = DOMAIN_ZONES.get(domain, [])
    chart_bits = _chart_lines_for_domain(anchors, domain)
    print_ok, print_bad = _print_lines_for_domain(zone_metrics, zones)
    human_verdict = _human_verdict_rewrite(domain, verdict, print_bad, [z for z in zones if z in zone_metrics and zone_metrics[z].get("readable")])

    parts = [f"<h4>{title}</h4>", f"<p class='body'><em>{conf}.</em> {human_verdict}</p>"]

    if chart_bits:
        parts.append("<p class='body'><strong>What your chart says:</strong> " + " ".join(chart_bits) + "</p>")

    if print_ok:
        parts.append(
            "<p class='body'><strong>What we could read on your palm photo:</strong> "
            + " ".join(print_ok[:3])
            + "</p>"
        )

    if print_bad:
        bad = ", ".join(print_bad)
        parts.append(
            f"<p class='body'><strong>Not readable on this print:</strong> "
            f"The {bad} zone(s) were too blurry to count lines reliably. "
            f"Re-upload a close-up of those fingers or mounts to complete this section.</p>"
        )

    return "".join(parts)


def human_confluence_html(analysis: dict[str, Any]) -> str:
    """Plain-English confluence - no duplicate technical bullets."""
    confluence = analysis.get("confluence") or []
    anchors = analysis.get("anchors") or []
    zone_metrics = analysis.get("zone_metrics") or {}
    has_photos = analysis.get("cv_inspected", False)

    if not confluence:
        return ""

    domain_paras = [
        _human_domain_paragraph(
            c["domain"], c["verdict"], c.get("confidence", "moderate"),
            anchors, zone_metrics,
        )
        for c in confluence
    ]

    intro = (
        "<p class='body'>This section merges your <strong>birth chart</strong> with what "
        "<strong>we actually saw</strong> on the palm photo. Where a zone was blurry, "
        "we say so plainly - we do not ask you to guess.</p>"
    )
    if not has_photos:
        intro = (
            "<p class='body'>No palm photos were analysed. The paragraphs below are "
            "<strong>chart-only</strong> guidance - upload both palms to add print verification.</p>"
        )

    # One combined retake note if many zones failed
    all_bad: set[str] = set()
    for dom in DOMAIN_ZONES:
        _, bad = _print_lines_for_domain(zone_metrics, DOMAIN_ZONES[dom])
        all_bad.update(bad)
    retake = ""
    if all_bad and has_photos:
        retake = (
            "<p class='fine'>To sharpen the overall read, close-ups needed for: "
            + ", ".join(sorted(all_bad))
            + " mounts. File as <code>left_index.jpg</code>, <code>right_pinky.jpg</code>, etc.</p>"
        )

    return (
        '<div class="section-h">Life reading - chart and palm together</div>'
        f'<div class="card blue">{intro}{"".join(domain_paras)}{retake}</div>'
    )


def anchor_analysis_html(analysis: dict[str, Any], cv_marked: list[dict] | None = None) -> str:
    zone_metrics = analysis.get("zone_metrics") or {}
    if not zone_metrics and cv_marked:
        from astro_palmistry_zone_cv import aggregate_zone_metrics
        zone_metrics = aggregate_zone_metrics([cv_marked])

    parts = [
        '<div class="note">CV has inspected your palm print in each marked zone. '
        "If a zone is blurry, the report states <strong>photo not clear</strong> instead of asking you to check.</div>",
    ]

    for a in analysis.get("anchors", []):
        zid = a["zone_id"]
        card_cls = "amber" if a["tone"] == "caution" else ("green" if a["tone"] == "support" else "")
        cv_block = f'<p class="body"><strong>Print inspection ({zid}):</strong> {a.get("cv_finding", "")}</p>'
        parts.append(
            f'<div class="card {card_cls}"><h3>Line main: {a["planet"]} in house {a["house"]} '
            f'({a["sign"]}, {a["dignity"].replace("_", " ")})</h3>'
            f'<p class="body"><strong>Chart palm zone:</strong> {a["palm"]}</p>'
            f'<p class="body"><strong>Chart reading:</strong> {a["life"]}</p>'
            + (f'<p class="body"><strong>Vs {a.get("chart_link_with", "the rest of the chart")}:</strong> '
               f'{a["chart_link"]}</p>' if a.get("chart_link") else "")
            + f'{cv_block}'
            '<table class="tl"><tr><th>Sub-planet</th><th>House</th><th>Chart</th><th>Print (CV)</th></tr>'
        )
        for s in a.get("sub_planets", []):
            rel = s.get("relative_to_anchor") or ""
            rel_html = f"<br/><span class='fine'>{rel}</span>" if rel else ""
            parts.append(
                f'<tr><td>{s["planet"]}</td><td>{s["house"]} {s["sign"]}</td>'
                f'<td>{s["life"]}{rel_html}</td>'
                f'<td>{s.get("cv_finding", "")}</td></tr>'
            )
        parts.append("</table></div>")

    parts.append(human_confluence_html(analysis))
    return "\n".join(parts)
