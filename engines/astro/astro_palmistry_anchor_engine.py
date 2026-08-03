#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Anchor planet (line main) + sub-planet house readings per Astro-Palmistry book.

If Jupiter is in 8th, Jupiter is the line-lord for the 8th-house palm zone.
Each other planet in its house is a sub-planet with its own palm mark and book meaning.
Confluence merges themes across anchors and sub-planets.
"""
from __future__ import annotations

from typing import Any

from astro_palmistry_zone_cv import DOMAIN_ZONES, cv_finding_sentence

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
    8: "longevity, legacies, sudden turns",
    9: "luck, father-guru, dharma",
    10: "career, status, authority",
    11: "gains, friends, fulfilment",
    12: "expenses, foreign, secret sorrows",
}

MAIN_LINE: dict[tuple[str, int], dict[str, str]] = {
    ("Jupiter", 8): {
        "palm": "Jupiter mount rayed; fate line bends toward Saturn; 8th-zone cross on life/heart lines.",
        "life": "Longevity and legacies house active. Debilitated Jupiter here is malefic for children and grandfather (book p.317). Alone in 8th/6th/10th stresses kalpayu themes.",
        "domain": "longevity",
        "tone": "caution",
    },
    ("Mercury", 10): {
        "palm": "Mercury mount under little finger; fate and Sun lines toward career sector.",
        "life": "Karma bhava. Debilitated Mercury: twisted career line, weak pinky mount; status through discipline.",
        "domain": "career",
        "tone": "caution",
    },
    ("Venus", 10): {
        "palm": "Venus mount full; girdle of Venus; Sun/fate lines to Apollo sector.",
        "life": "Exalted Venus in 10th supports public career, comfort, arts or finance visibility.",
        "domain": "career",
        "tone": "support",
    },
    ("Ketu", 5): {
        "palm": "Upper Mars (Ketu sector) + Venus/Moon mounts; heart and children lines.",
        "life": "Ketu in 5th: children, ears, spine, knees; maternal uncle themes (book).",
        "domain": "children",
        "tone": "caution",
    },
    ("Mars", 11): {
        "palm": "Plain of Mars and gain branches on heart/life lines; Venus/Sun mounts.",
        "life": "Mars in 11th with moolatrikona: gains, elder siblings, fulfilled desires; Rahu co-tenant amplifies node marks.",
        "domain": "gains",
        "tone": "support",
    },
    ("Rahu", 11): {
        "palm": "Zone above Heart line (Rahu) plus 11th gain lines on Sun/Venus mounts.",
        "life": "Rahu in 11th: unconventional gains; check Rahu zone for heavy cross-lines.",
        "domain": "gains",
        "tone": "mixed",
    },
    ("Saturn", 6): {
        "palm": "Saturn mount; Hepatica/health lines; upper Mars sector.",
        "life": "Service, debt, enemy house. Saturn here: fate line bars, chronic strain themes.",
        "domain": "health",
        "tone": "caution",
    },
    ("Moon", 4): {
        "palm": "Mount of Moon at percussion; heart line base toward Luna; fate branches.",
        "life": "Mother, home, property. Moon in 4th: domestic comfort or worry per mount clarity.",
        "domain": "home",
        "tone": "mixed",
    },
    ("Sun", 9): {
        "palm": "Sun mount, intuition/travel lines, ring of Solomon area.",
        "life": "Bhagya house: father, guru, long travel; Sun line toward Libra/Venus sector if strong.",
        "domain": "luck",
        "tone": "support",
    },
}

SUB_PLANET: dict[tuple[str, int], dict[str, str]] = {
    ("Ketu", 5): {
        "palm": "Upper Mars grille; Venus mount children lines.",
        "life": "Children/creativity house stressed per chart; ears, spine, knees themes.",
        "domain": "children",
        "tone": "caution",
    },
    ("Mercury", 10): {
        "palm": "Little-finger mount; fate line twist.",
        "life": "Career and reputation; debility makes Mercury malefic when 8th is also afflicted.",
        "domain": "career",
        "tone": "caution",
    },
    ("Venus", 10): {
        "palm": "Strong Venus mount; clean girdle.",
        "life": "Public comfort and career grace; exaltation supports arts, partnership, finance.",
        "domain": "career",
        "tone": "support",
    },
    ("Jupiter", 8): {
        "palm": "Jupiter mount + fate toward Saturn.",
        "life": "8th-house anchor: legacies, sudden events; debilitated = malefic for progeny line.",
        "domain": "longevity",
        "tone": "caution",
    },
    ("Saturn", 6): {
        "palm": "Saturn mount barred; health lines.",
        "life": "Service, illness, enemies; dusthana Saturn strains fate line.",
        "domain": "health",
        "tone": "caution",
    },
    ("Mars", 11): {
        "palm": "Plain of Mars active; gain branches.",
        "life": "Gains through courage, friends, elder siblings; strong Mars supports income lines.",
        "domain": "gains",
        "tone": "support",
    },
    ("Rahu", 11): {
        "palm": "Rahu zone above heart; Sun/Venus gain lines.",
        "life": "Gains through unconventional paths; co-tenant with Mars doubles Plain of Mars activity.",
        "domain": "gains",
        "tone": "mixed",
    },
    ("Moon", 4): {
        "palm": "Luna mount; life branch toward Moon.",
        "life": "Mother, home, vehicles; Moon mount fullness = domestic stability.",
        "domain": "home",
        "tone": "mixed",
    },
    ("Sun", 9): {
        "palm": "Sun line to mount; travel marks.",
        "life": "Luck, father, dharma; strong Sun line toward Venus/Libra = reasonable income (book).",
        "domain": "luck",
        "tone": "support",
    },
}

RELATIVE_SUB: dict[tuple[str, int], list[tuple[tuple[str, int], str]]] = {
    ("Jupiter", 8): [
        (("Ketu", 5), "With Jupiter anchoring 8th, Ketu in 5th pulls children stress onto upper-Mars and Venus mounts while 8th Jupiter strains progeny/grandfather line (book)."),
        (("Mercury", 10), "8th malefic Jupiter makes Mercury in 10th more troubled: career fate line twisted, pinky mount weak (book: Mercury malefic when 8th afflicted)."),
        (("Venus", 10), "Venus exalted in 10th partly rescues career mount despite Jupiter@8 strain on legacy line."),
        (("Saturn", 6), "Saturn in 6th with Jupiter@8: health/service bars on fate line; dusthana echo on both mounts."),
        (("Mars", 11), "Mars+Rahu in 11th offsets some 8th Jupiter loss through active Plain of Mars and Rahu zone."),
        (("Moon", 4), "Moon in 4th home zone vs 8th Jupiter: property comfort parallel to legacy/sudden-turn stress."),
        (("Sun", 9), "Sun in 9th luck house supports dharma/travel lines while Jupiter@8 handles legacy separately."),
        (("Rahu", 11), "Rahu with Mars in 11th: mark Rahu above heart and Plain of Mars together."),
    ],
}

TONE_SCORE = {"support": 2, "mixed": 0, "caution": -2}


def _fallback_main(planet: str, house: int, dignity: str, sign: str) -> dict[str, str]:
    zone = PLANET_ZONE.get(planet, "mars")
    return {
        "palm": f"Mark {zone} mount/zone for {planet} as line-lord of house {house}.",
        "life": f"{planet} in {sign} ({dignity.replace('_', ' ')}) rules {HOUSE_THEMES.get(house, 'house matters')} on the palm.",
        "domain": HOUSE_THEMES.get(house, "general").split(",")[0].strip(),
        "tone": "caution" if dignity == "debilitated" else "mixed",
    }


def _fallback_sub(planet: str, house: int, dignity: str, sign: str) -> dict[str, str]:
    zone = PLANET_ZONE.get(planet, "mars")
    return {
        "palm": f"Sub-zone: {zone} for {planet} in house {house}.",
        "life": f"{planet} in {sign} ({dignity.replace('_', ' ')}) affects {HOUSE_THEMES.get(house, 'this life area')}.",
        "domain": HOUSE_THEMES.get(house, "general").split(",")[0].strip(),
        "tone": "caution" if dignity == "debilitated" else ("support" if dignity == "exalted" else "mixed"),
    }


def build_anchor_analysis(planets: dict[str, dict], lagna: str) -> dict[str, Any]:
    plist = sorted(
        [(p, d) for p, d in planets.items()],
        key=lambda x: (-1 if x[1].get("dignity") == "debilitated" else 0, x[1].get("house", 99)),
    )

    anchors: list[dict[str, Any]] = []
    for planet, info in plist:
        h = int(info["house"])
        main = MAIN_LINE.get((planet, h)) or _fallback_main(planet, h, info["dignity"], info["sign"])
        subs: list[dict[str, Any]] = []
        for sp, si in plist:
            if sp == planet:
                continue
            sh = int(si["house"])
            sub = SUB_PLANET.get((sp, sh)) or _fallback_sub(sp, sh, si["dignity"], si["sign"])
            rel = ""
            for (ap, ah), pairs in RELATIVE_SUB.items():
                if ap == planet and ah == h:
                    for (rp, rh), msg in pairs:
                        if rp == sp and rh == sh:
                            rel = msg
                            break
            subs.append({
                "planet": sp,
                "sign": si["sign"],
                "house": sh,
                "dignity": si["dignity"],
                "zone_id": PLANET_ZONE.get(sp, "mars"),
                "palm": sub["palm"],
                "life": sub["life"],
                "domain": sub["domain"],
                "tone": sub["tone"],
                "relative_to_anchor": rel,
            })
        anchors.append({
            "planet": planet,
            "sign": info["sign"],
            "house": h,
            "dignity": info["dignity"],
            "zone_id": PLANET_ZONE.get(planet, "mars"),
            "role": "line_main",
            "palm": main["palm"],
            "life": main["life"],
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

    ketu_a = next((x for x in anchors if x["planet"] == "Ketu" and x["house"] == 5), None)
    jup_a = next((x for x in anchors if x["planet"] == "Jupiter" and x["house"] == 8), None)
    if ketu_a and jup_a:
        for s in jup_a.get("sub_planets", []):
            if s["planet"] == "Ketu" and s["house"] == 5 and s.get("relative_to_anchor"):
                ketu_a["chart_link"] = s["relative_to_anchor"]

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
            _add(dom, a["planet"], a["house"], "link", f"{a['planet']}@{a['house']} (vs Jupiter@8): {a['chart_link'][:120]}")
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
        elif stress_confirmed and chart_score <= 0:
            verdict = (
                f"Chart stress for {dom} is visible on your print - dense lines in "
                f"{', '.join(stress_confirmed)} zone(s)."
            )
            conf = "moderate-high"
        elif sparse and chart_score <= 0:
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
    "longevity": "Longevity & legacy",
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
                        lines.append(f"{s['planet']} in the {s['house']}th ({s['sign']}) - {s['life']}")
            continue
        k = (a["planet"], a["house"])
        if k not in seen:
            seen.add(k)
            lines.append(f"{a['planet']} in the {a['house']}th ({a['sign']}) - {a['life']}")
        for s in a.get("sub_planets", []):
            if s.get("domain") == domain:
                sk = (s["planet"], s["house"])
                if sk not in seen:
                    seen.add(sk)
                    rel = s.get("relative_to_anchor") or ""
                    extra = f" This links to {a['planet']} in the {a['house']}th house: {rel}" if rel else ""
                    lines.append(f"{s['planet']} in the {s['house']}th ({s['sign']}) - {s['life']}{extra}")
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
            + (f'<p class="body"><strong>Vs Jupiter@8:</strong> {a["chart_link"]}</p>' if a.get("chart_link") else "")
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
