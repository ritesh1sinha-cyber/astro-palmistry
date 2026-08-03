#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Section-by-section Jaimini book analysis (structure chart, not dasha timing)."""
from __future__ import annotations

from dataclasses import dataclass

from jaimini_book_data import (
    argala_quality,
    lookup_kl_house_theme,
    lookup_kl_occupation,
    lookup_planet_kl_house,
)
from jaimini_books_chart import (
    DUAL,
    FIXED,
    MOVABLE,
    NAT_BENEFIC,
    NAT_MALEFIC,
    ROLE_ORDER,
    ROLE_SHORT,
    JaiminiBooksChart,
    _ord,
    house_of,
    sign_aspects_from,
    sign_at,
)


@dataclass
class BookSection:
    section_id: str
    book: str
    title: str
    rules: str
    prediction: str
    fact: str
    book_quote: str
    tone: str = "neutral"  # good | attention | neutral


def _clip(t: str, n: int = 380) -> str:
    t = " ".join(t.split())
    return t if len(t) <= n else t[: n - 1].rsplit(" ", 1)[0] + "..."


def _tone_from_open(open_n: int, blocked_n: int) -> str:
    if open_n >= 2 and blocked_n == 0:
        return "good"
    if blocked_n >= 2:
        return "attention"
    return "neutral"


def analyze_all_sections(chart: JaiminiBooksChart, book: dict) -> list[BookSection]:
    out: list[BookSection] = []
    for spec in book.get("report_sections", []):
        fn = _ANALYZERS.get(spec["id"])
        if fn:
            out.append(fn(chart, book, spec))
    return out


def _sec_goel_mindset(c, b, spec):
    basics = b.get("goel_basics", [])
    q = basics[0] if basics else "Jaimini uses sign-based aspects and variable cara karakas."
    pred = (
        f"Your chart is read Jaimini-first here: {c.lagna} lagna with "
        f"Karakamsha {c.karakamsa or 'unknown'}. "
        "This lane judges structure (karakas, KL, argala, raja yoga) alongside the Chara dasha timing sections above."
    )
    return BookSection(
        spec["id"], spec["book"], spec["title"], spec["rules"], pred,
        f"Birth lagna {c.lagna}; AK {c.role('Atmakarak').get('planet', '?')}.",
        _clip(q), "neutral",
    )


def _sec_goel_sign_aspects(c, b, spec):
    asp = sign_aspects_from(c.lagna)
    hits = []
    for s in sorted(asp, key=lambda x: ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                                         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"].index(x)):
        pl = c.planets_in(s)
        if pl:
            hits.append(f"{', '.join(pl)} in {s} ({_ord(house_of(s, c.lagna))} house)")
    cat = "movable" if c.lagna in MOVABLE else ("fixed" if c.lagna in FIXED else "dual")
    pred = (
        f"From {c.lagna} ({cat} lagna), Jaimini sign-aspects reach specific signs without counting every Parashari drishti. "
        + (f"Planets activated by sign-aspect: {'; '.join(hits[:4])}." if hits else
           "No planets sit in the primary aspected signs - sign-aspect support is quiet.")
    )
    return BookSection(
        spec["id"], spec["book"], spec["title"], spec["rules"], pred,
        f"Lagna category: {cat}; aspected signs include {', '.join(sorted(asp)[:4])}...",
        "Movable aspects fixed (except adjacent); fixed aspects movable; dual aspects dual (Goel Part B).",
        "good" if hits else "neutral",
    )


def _sec_goel_karakas(c, b, spec):
    roles = b.get("karaka_roles", {})
    lines = []
    for r in ROLE_ORDER:
        k = c.role(r)
        if not k:
            continue
        meaning = roles.get(r, "")
        lines.append(
            f"{ROLE_SHORT[r]} {k['planet']} in {k['sign']} ({_ord(k['house'])} from lagna): {meaning}"
        )
    pred = (
        "Seven cara karakas rank soul roles by degree order among Sun through Saturn. "
        + " ".join(_clip(x, 120) for x in lines[:4])
        + ("..." if len(lines) > 4 else "")
    )
    ak = c.role("Atmakarak")
    return BookSection(
        spec["id"], spec["book"], spec["title"], spec["rules"], pred,
        f"AK={ak.get('planet')} AmK={c.role('Amatyakarak').get('planet')} DK={c.role('Darakaraka').get('planet')}.",
        _clip(roles.get("Atmakarak", "")),
        "good" if ak.get("dignity") in ("exalted", "own_sign", "moolatrikona") else "neutral",
    )


def _sec_goel_three_lagnas(c, b, spec):
    kl = c.karakamsa or "?"
    pred = (
        f"Goel's three lenses: Karakamsha ({kl}) = inner promise; birth lagna ({c.lagna}) = will and aspiration; "
        f"Arudha lagna ({c.arudha_lagna}) = public image. "
    )
    if c.arudha_lagna != kl:
        pred += "KL and Arudha differ - inner wiring and outer image may not match; reputation can run ahead of private comfort."
    else:
        pred += "KL and Arudha align - what you project and what you are underneath read consistently."
    return BookSection(
        spec["id"], spec["book"], spec["title"], spec["rules"], pred,
        f"KL {kl}, lagna {c.lagna}, AL {c.arudha_lagna}.",
        "Three lagna lenses: Karakamsha inner truth, lagna will, Arudha image (Goel Part C).",
        "neutral",
    )


def _sec_goel_arudha(c, b, spec):
    pred = (
        f"Arudha lagna {c.arudha_lagna} colours how society reads you; Upapada {c.upapada} scripts marriage and partnership. "
        f"Upapada tenants: {', '.join(c.planets_in(c.upapada)) or 'none'}. "
        "Goel stresses Upapada for all relationship assessment in Jaimini."
    )
    dk = c.role("Darakaraka")
    pred += f" Dara karaka {dk.get('planet')} in {_ord(dk.get('house', 0))} house colours partner type alongside Upapada."
    return BookSection(
        spec["id"], spec["book"], spec["title"], spec["rules"], pred,
        f"AL={c.arudha_lagna}, UP={c.upapada}, DK={dk.get('planet')}.",
        "Twelfth-house Arudha is Upapada - primary for relationships (Goel Part D).",
        "good" if c.planets_in(c.upapada) and any(p in NAT_BENEFIC for p in c.planets_in(c.upapada)) else "neutral",
    )


def _sec_goel_raja_yoga(c, b, spec):
    pairs = c.raja_yoga_pairs()
    amk, ak = c.role("Amatyakarak"), c.role("Atmakarak")
    extra = []
    if amk.get("sign") and ak.get("sign"):
        rel = house_of(amk["sign"], ak["sign"])
        if rel in (1, 4, 5, 7, 9, 10, 11):
            extra.append(f"AmK in {_ord(rel)} from AK sign - success with less struggle (Goel).")
        elif rel in (6, 8, 12):
            extra.append(f"AmK in trika {_ord(rel)} from AK - success after hard work.")
    if c.role("Amatyakarak").get("house") in (3, 6):
        extra.append("AmK in 3rd or 6th - professional skill indicator per Goel.")
    pred = (
        ("Strong Jaimini raja yoga material: " + "; ".join(pairs[:3]) + ". " if pairs else
         "No major karaka-pair yoga by conjunction/sign aspect in this scan. ")
        + " ".join(extra)
        + " Check D9 repetition - Goel says yogas there deliver easier."
    )
    quote = b.get("goel_raja_yoga_pairs", ["AK+AmK mutual aspect"])[0]
    return BookSection(
        spec["id"], spec["book"], spec["title"], spec["rules"], pred,
        f"{len(pairs)} karaka-pair yogas; AmK house {_ord(amk.get('house', 0))}.",
        _clip(quote),
        "good" if pairs else "neutral",
    )


def _sec_goel_argala_lagna(c, b, spec):
    ag = c.argala_on(c.lagna)
    rules = b.get("goel_argala_rules", [])
    pred = (
        ("Open argala on lagna from: " + "; ".join(ag["open"]) + ". " if ag["open"] else "No clean open argala on lagna. ")
        + ("Mixed/blocked: " + "; ".join(ag["blocked"]) + ". " if ag["blocked"] else "")
        + ("Viparita argala: three+ malefics in 3rd from lagna - very favourable (Goel)." if ag["viparita"] else "")
    )
    if not pred.strip():
        pred = "Argala on lagna is weak - results depend more on karakas and KL than on intervention support."
    return BookSection(
        spec["id"], spec["book"], spec["title"], spec["rules"], pred,
        f"Open argala houses: {ag['open_houses'] or 'none'}.",
        _clip(rules[0] if rules else "Argala from 4th, 2nd, 11th; obstruction 10th, 12th, 3rd."),
        _tone_from_open(len(ag["open"]), len(ag["blocked"])),
    )


def _sec_gems_kl_intro(c, b, spec):
    pred = (
        f"Marc Boney (Gems) applies graha effects from Karakamsha lagna {c.karakamsa or '?'} "
        "in both D1 (karakamsha) and D9 (svamsa). This is the inner-promise chart: innate quality, "
        "occupation bent, and moksha potential - separate from Chara dasha seasons."
    )
    return BookSection(
        spec["id"], spec["book"], spec["title"], spec["rules"], pred,
        f"AK {c.role('Atmakarak').get('planet')} -> KL {c.karakamsa}.",
        "K.N. Rao: apply KL in birth chart and navamsha; Boney adopts two-fold karakamsha/svamsa read.",
        "neutral",
    )


def _sec_gems_kl_argala(c, b, spec):
    if not c.karakamsa:
        return BookSection(spec["id"], spec["book"], spec["title"], spec["rules"],
                           "Karakamsha unavailable - cannot read argala from KL.", "KL missing.", "", "attention")
    ag = c.argala_on(c.karakamsa)
    pred = (
        f"Argala from Karakamsha {c.karakamsa}: "
        + ("support from " + "; ".join(ag["open"]) if ag["open"] else "no unobstructed argala")
        + (". Blocked: " + "; ".join(ag["blocked"]) if ag["blocked"] else "")
        + ". Gems: unobstructed argala preserves and amplifies house results."
    )
    return BookSection(
        spec["id"], spec["book"], spec["title"], spec["rules"], pred,
        f"KL argala open on houses {ag['open_houses']}.",
        "Principal argala: 2nd, 4th, 11th from reference; obstruction 12th, 10th, 3rd (Gems ch. Argala).",
        _tone_from_open(len(ag["open"]), len(ag["blocked"])),
    )


def _kl_house_section(c, b, spec, house: int, domain: str, default_quote: str):
    if not c.karakamsa:
        return BookSection(spec["id"], spec["book"], spec["title"], spec["rules"],
                           f"Karakamsha missing - skip {domain}.", "KL not computed.", "", "attention")
    pls = c.planets_in_kl_house(house)
    theme = lookup_kl_house_theme(b, house) or default_quote
    clauses = []
    for pl in pls:
        txt = lookup_planet_kl_house(b, pl, house)
        clauses.append(f"{pl}: {_clip(txt or theme, 160)}")
    if pls:
        pred = f"For {domain}, {_ord(house)} from KL ({c.karakamsa}) holds {', '.join(pls)}. " + " ".join(clauses[:2])
    else:
        pred = f"No planets in {_ord(house)} from KL ({c.karakamsa}) for {domain}. Theme when activated: {_clip(theme, 200)}."
    return BookSection(
        spec["id"], spec["book"], spec["title"], spec["rules"], pred,
        f"Sign {sign_at(c.karakamsa, house)}; planets: {', '.join(pls) or 'none'}.",
        _clip(theme),
        "good" if pls and any(p in NAT_BENEFIC for p in pls) else "neutral",
    )


def _sec_gems_kl_occupation(c, b, spec):
    if not c.karakamsa:
        return BookSection(spec["id"], spec["book"], spec["title"], spec["rules"],
                           "Karakamsha missing.", "", "", "attention")
    lines = []
    kl_sign = c.karakamsa
    for pl, info in c.pc["planets"].items():
        kh = c.kl_house(info["sign"])
        if kh in (1, 2):
            occ = lookup_kl_occupation(b, pl)
            if occ:
                lines.append(f"{pl} in {_ord(kh)} from KL: {_clip(occ, 150)}")
    akp = c.role("Atmakarak").get("planet", "")
    pred = (
        f"Gems sutras judge occupation from planets in or on Karakamsha lagna {kl_sign} and 2nd from there. "
        + (" ".join(lines[:4]) if lines else f"AK {akp} anchors inner lagna: {_clip(lookup_kl_occupation(b, akp), 180)}")
    )
    return BookSection(
        spec["id"], spec["book"], spec["title"], spec["rules"], pred,
        f"KL {kl_sign}; {len(lines)} occupation hits.",
        _clip(lookup_kl_occupation(b, akp)),
        "good" if lines else "neutral",
    )


def _sec_gems_kl_10th(c, b, spec):
    return _kl_house_section(c, b, spec, 10, "career and public accomplishment",
                             "Mercury on 10th from KL gives Saturn-like professional accomplishment.")


def _sec_gems_kl_4th(c, b, spec):
    return _kl_house_section(c, b, spec, 4, "home, property and emotional base",
                             "Moon-Venus on 4th from KL can give palatial home.")


def _sec_gems_kl_9th(c, b, spec):
    return _kl_house_section(c, b, spec, 9, "dharma, guru and truthful conduct",
                             "Benefics on 9th from KL: virtuous, truthful, guru-devoted.")


def _sec_gems_kl_5th(c, b, spec):
    return _kl_house_section(c, b, spec, 5, "knowledge, creativity and authorship",
                             "Moon and Jupiter in 5th from KL indicate author/intelligence.")


def _sec_gems_kl_12th_moksha(c, b, spec):
    return _kl_house_section(c, b, spec, 12, "moksha and afterlife realm",
                             "Exalted benefic in 12th from KL: blissful realm; Ketu with benefic: liberation potential.")


def _sec_gems_kl_12th_devotion(c, b, spec):
    pls = c.planets_in_kl_house(12) if c.karakamsa else []
    pred = (
        "Gems links 12th-from-KL to Ista Devata devotion when benefics and Ketu combine in moksha signs. "
        + (f"Your 12th-from-KL planets: {', '.join(pls)} - spiritual practice and retreat themes are alive."
           if pls else "No strong 12th-from-KL tenant - devotion is optional, not the central life script.")
    )
    return BookSection(
        spec["id"], spec["book"], spec["title"], spec["rules"], pred,
        f"12th-from-KL: {', '.join(pls) or 'empty'}.",
        "12th from karakamsha: deity devotion and moksha refinement (Gems Part 12th House).",
        "good" if pls and any(p in ("Ketu", "Jupiter", "Venus") for p in pls) else "neutral",
    )


def _sec_jewels_argala_quality(c, b, spec):
    ag = c.argala_on(c.lagna)
    benefic = malefic = 0
    for ah in (4, 2, 11):
        for p in c.planets_in(sign_at(c.lagna, ah)):
            if p in NAT_BENEFIC:
                benefic += 1
            else:
                malefic += 1
    tier = argala_quality(b, benefic, malefic, len(ag["open_houses"]))
    tiers = b.get("jewels_argala_tiers", {})
    sample = (tiers.get(tier) or [""])[0] if tier in tiers else ""
    pred = (
        f"Jewels grades argala quality for yogada support: {tier.replace('_', ' ')} tier on lagna. "
        + (_clip(sample) if sample else "Better argala tiers sustain raja yoga delivery.")
    )
    return BookSection(
        spec["id"], spec["book"], spec["title"], spec["rules"], pred,
        f"Benefic {benefic}, malefic {malefic} in argala positions.",
        _clip(sample or "Superior argala: benefics with strength in multiple argala positions."),
        "good" if tier == "superior" else ("attention" if tier == "average" else "neutral"),
    )


def _sec_jewels_yogada(c, b, spec):
    rules = b.get("jewels_yogada_rules", [])
    pred = (
        "Jewels: planets become yogadas by conjoining or sign-aspecting bhava, hora, ghatika lagnas "
        "and 1st/7th in rasi, navamsha, drekkana. "
        "Special lagnas (hora/ghatika) are not in this extract - yogada scan is partial. "
        "Use full software export for complete Jewels yogada checklist."
    )
    if c.raja_yoga_pairs():
        pred += f" Karaka-pair yogas present ({len(c.raja_yoga_pairs())}) support status even without hora/ghatika data."
    return BookSection(
        spec["id"], spec["book"], spec["title"], spec["rules"], pred,
        "Hora/Ghatika lagna not in standard extract.",
        _clip(rules[0] if rules else "Yogada planet on special lagnas + unobstructed argala = reliable fortune."),
        "neutral",
    )


_ANALYZERS = {
    "goel_mindset": _sec_goel_mindset,
    "goel_sign_aspects": _sec_goel_sign_aspects,
    "goel_karakas": _sec_goel_karakas,
    "goel_three_lagnas": _sec_goel_three_lagnas,
    "goel_arudha": _sec_goel_arudha,
    "goel_raja_yoga": _sec_goel_raja_yoga,
    "goel_argala_lagna": _sec_goel_argala_lagna,
    "gems_kl_intro": _sec_gems_kl_intro,
    "gems_kl_argala": _sec_gems_kl_argala,
    "gems_kl_occupation": _sec_gems_kl_occupation,
    "gems_kl_10th": _sec_gems_kl_10th,
    "gems_kl_4th": _sec_gems_kl_4th,
    "gems_kl_9th": _sec_gems_kl_9th,
    "gems_kl_5th": _sec_gems_kl_5th,
    "gems_kl_12th_moksha": _sec_gems_kl_12th_moksha,
    "gems_kl_12th_devotion": _sec_gems_kl_12th_devotion,
    "jewels_argala_quality": _sec_jewels_argala_quality,
    "jewels_yogada": _sec_jewels_yogada,
}
