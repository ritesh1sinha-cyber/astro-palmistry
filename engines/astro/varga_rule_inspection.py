#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Book-rule inspection for divisional charts.

Goel's divisional-chart books do not stop at house-by-house reading. Each
chapter states *rules* and illustrates them with *named example charts* where
the author highlights a decisive combination. This module walks every such
rule/topic for a given varga, tests it against the client's own chart, and
returns human-relatable findings. Findings that match a combination the author
specifically emphasised in a worked example are marked ``highlight=True`` so the
report can paint them in a distinct colour.

The intent is prediction-first, plain-English output (no jargon dumps).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from goel_varga import SIGNS, house_from_lagna, house_from_sign

SIGN_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}

# Book "special nomenclature" — which D1 house a planet's navamsha sign falls in
# (Goel, D9 ch.1, Method 1). 6 / 8 / 12 spoil; kendra/trikona/2/11 strengthen.
NAVAMSHA_HOUSE_NAME = {
    1: "Lagnamsha (self)", 2: "Vittamsha (wealth)", 3: "Bhratamsha (sibling)",
    4: "Sukhamsha (comfort)", 5: "Putramsha (children)", 6: "Shastamsha (illness/debt)",
    7: "Bharyamsha (spouse)", 8: "Nidhanamsha (loss/death)", 9: "Bhagyamsha (fortune)",
    10: "Karmamsha (career)", 11: "Labhamsha (gains)", 12: "Vyamsha (expenses)",
}
SPOIL_HOUSES = {6, 8, 12}
GOOD_NAVAMSHA_HOUSES = {1, 2, 4, 5, 7, 9, 10, 11}


@dataclass
class RuleFinding:
    """One book rule/topic tested against the client chart."""
    topic: str
    verdict: str          # "favourable" | "caution" | "neutral" | "info"
    detail: str           # plain-English sentence for the client
    highlight: bool = False   # matches an author-emphasised worked example
    why: str = ""         # short technical evidence (collapsible / muted)
    chapter: str = ""     # book chapter reference


_VERDICT_BADGE = {
    "favourable": ("Supportive", "pos"),
    "caution": ("Watch this", "cau"),
    "neutral": ("Balanced", "neu"),
    "info": ("Noted", "neu"),
}


# ----------------------------------------------------------------------------
# D9 — Navamsha (marriage, spouse, dharma, inner maturity)
# ----------------------------------------------------------------------------
def inspect_d9(d9: dict, pc: dict, nav: dict) -> list[RuleFinding]:
    out: list[RuleFinding] = []
    d1_lagna = d9.get("d1_lagna", "")
    planets = d9.get("planets", {})

    # --- Author example rule 1: lagna lord's navamsha sign == D1 8th sign ---
    # Jatakdeshmarg verse (Indira Gandhi / Mahatma Gandhi example): lagna lord
    # in the navamsha of the 8th sign — a severe, author-highlighted caution.
    ll = d9.get("lagna_lord", "")
    ll_b = planets.get(ll, {})
    if d1_lagna and ll_b.get("sign"):
        eighth_sign = SIGNS[(SIGNS.index(d1_lagna) + 7) % 12]
        if ll_b["sign"] == eighth_sign:
            out.append(RuleFinding(
                topic="Lagna lord in the 8th navamsha (classic warning verse)",
                verdict="caution",
                detail=(
                    f"Your ascendant lord {ll} sits in the navamsha of your birth "
                    f"chart's 8th sign. The classics flag this as a vulnerability for "
                    f"vitality and self-support late in life — treat it as a nudge to "
                    f"keep close relationships and health well looked after, not as fate."
                ),
                highlight=True,
                why=f"{ll} D9 sign {ll_b['sign']} = D1 8th sign {eighth_sign}",
                chapter="D9 Ch.1 (Jatakdeshmarg verse)",
            ))

    # --- Author example rule 2: 7th lord's navamsha sign == D1 2nd sign ---
    # "If the lord of 7th occupies the navamsha sign of the 2nd house, the
    # spouse will be of loose character" (2nd is 8th from 7th). Highlighted.
    lord7_d1 = nav.get("lord7_d1", "")
    l7b = planets.get(lord7_d1, {})
    if d1_lagna and l7b.get("sign"):
        second_sign = SIGNS[(SIGNS.index(d1_lagna) + 1) % 12]
        if l7b["sign"] == second_sign:
            out.append(RuleFinding(
                topic="7th lord in the 2nd navamsha (spouse-conduct verse)",
                verdict="caution",
                detail=(
                    f"Your marriage lord {lord7_d1} falls in the navamsha of your 2nd "
                    f"sign — the 8th from partnership. The text reads this as friction "
                    f"around the partner's habits or values; in practice, align "
                    f"expectations early and choose a partner whose values you share."
                ),
                highlight=True,
                why=f"{lord7_d1} D9 sign {l7b['sign']} = D1 2nd sign {second_sign}",
                chapter="D9 Ch.1 (spouse character verse)",
            ))

    # --- Author example rule 3: any house lord landing in 6/8/12 navamsha ---
    # "Lord of any house placed in Shastamsha, Nidhanamsha or Vyamsha is bad for
    # that house." Walk all 12 house lords. Highlight the spoiled ones.
    spoiled: list[str] = []
    HOUSE_TOPIC = {
        1: "your health & drive", 2: "family wealth & speech", 3: "courage & siblings",
        4: "home & peace of mind", 5: "children & creativity", 6: "rivals & debts",
        7: "marriage & partnership", 8: "longevity & shared resources",
        9: "fortune & father", 10: "career & status", 11: "gains & friends",
        12: "expenses & rest",
    }
    for h in range(1, 13):
        d1_house_sign = SIGNS[(SIGNS.index(d1_lagna) + h - 1) % 12] if d1_lagna else ""
        lord = SIGN_LORD.get(d1_house_sign, "")
        lb = planets.get(lord, {})
        if not lb.get("sign"):
            continue
        nh = house_from_sign(lb["sign"], d1_lagna)
        if nh in SPOIL_HOUSES:
            spoiled.append(
                f"the {_ord(h)} house ({HOUSE_TOPIC[h]}) — its lord {lord} drops into "
                f"{NAVAMSHA_HOUSE_NAME[nh].split('(')[0].strip()}"
            )
    if spoiled:
        lead = spoiled[0]
        extra = (
            f" Similar strain shows for {len(spoiled) - 1} more area"
            f"{'s' if len(spoiled) > 2 else ''}." if len(spoiled) > 1 else ""
        )
        out.append(RuleFinding(
            topic="House lords falling into weak navamsha (Method 1)",
            verdict="caution",
            detail=(
                f"Reading each life area's ruler in the navamsha, {lead} — the book "
                f"says this area needs extra care and matures only with effort.{extra}"
            ),
            highlight=True,
            why="; ".join(spoiled),
            chapter="D9 Ch.1 (Method 1 / special nomenclature)",
        ))

    # --- Beeja / Rashi Tulya strength (kendra/trikona lands) ---
    bstrong = nav.get("beeja_strong", [])
    bweak = nav.get("beeja_weak", [])
    if bstrong or bweak:
        out.append(RuleFinding(
            topic="Beeja / Rashi-Tulya navamsha strength",
            verdict="favourable" if len(bstrong) >= len(bweak) else "neutral",
            detail=(
                f"When your planets are recast by the navamsha sign they occupy, "
                f"{len(bstrong)} land in strong, supportive houses and {len(bweak)} in "
                f"testing ones. A majority in good houses points to an inner seed "
                f"(beeja) of strength that carries you through rough patches."
            ),
            why="; ".join(bstrong[:3] + bweak[:2]),
            chapter="D9 Ch.6 (Beeja / Rashi Tulya)",
        ))

    # --- Pushkar navamsha (author-emphasised auspicious placement) ---
    pushkar = [p for p, b in planets.items() if b.get("pushkar")]
    if pushkar:
        out.append(RuleFinding(
            topic="Pushkar navamsha (nourishing degrees)",
            verdict="favourable",
            detail=(
                f"{_join(pushkar)} {_v(pushkar, 'sits', 'sit')} in pushkar navamsha — "
                f"degrees the author calls nourishing and lucky. What "
                f"{_v(pushkar, 'this planet signifies', 'these planets signify')} tends "
                f"to be protected and to recover well even after setbacks."
            ),
            highlight=True,
            why=f"Pushkar: {', '.join(pushkar)}",
            chapter="D9 Ch.1 (Pushkar navamsha)",
        ))

    # --- Vargottama (same sign D1 & D9) ---
    vgt = [p for p, b in planets.items() if b.get("vargottama")]
    if d9.get("vargottama_lagna"):
        vgt = ["the ascendant"] + vgt
    if vgt:
        out.append(RuleFinding(
            topic="Vargottama (repeats sign in D1 & D9)",
            verdict="favourable",
            detail=(
                f"{_join(vgt)} {_v(vgt, 'repeats', 'repeat')} the same sign in both "
                f"birth and navamsha charts. This is a mark of consistency — these "
                f"significations hold firm and deliver what the birth chart promises."
            ),
            highlight=True,
            why=f"Vargottama: {', '.join(vgt)}",
            chapter="D9 Ch.1 (Vargottama)",
        ))

    # --- Vish navamsha (author-flagged harmful degrees) ---
    vish = [p for p, b in planets.items() if b.get("vish")]
    if vish:
        out.append(RuleFinding(
            topic="Vish navamsha (sensitive degrees)",
            verdict="caution",
            detail=(
                f"{_join(vish)} {_v(vish, 'falls', 'fall')} in vish navamsha — degrees "
                f"the author warns can undercut that planet's good results during its "
                f"dasha. Plan important moves around these periods rather than forcing "
                f"them."
            ),
            highlight=True,
            why=f"Vish: {', '.join(vish)}",
            chapter="D9 Ch.1 / Ch.7 (Vish navamsha)",
        ))

    # --- Marriage promise (D1 7th + D9 7th + denial scan) ---
    denial = nav.get("denial_hits", [])
    out.append(RuleFinding(
        topic="Marriage promise",
        verdict="caution" if len(denial) >= 2 else "favourable",
        detail=(
            "The marriage axis is well supported — the chart promises partnership "
            "and there is no strong denial pattern."
            if not denial else
            f"The chart shows {len(denial)} caution{'s' if len(denial) > 1 else ''} on "
            f"the marriage axis. This rarely means denial outright — more often "
            f"delay, deliberate choice, or extra effort to make union work."
        ),
        highlight=bool(denial),
        why="; ".join(denial) if denial else "No denial rule fired",
        chapter="D9 Ch.2 (marriage promise / denial)",
    ))

    # --- Marriage quality via karaka (Venus/Jupiter) ---
    kn = nav.get("marriage_karaka") or []
    if kn:
        out.append(RuleFinding(
            topic="Marriage quality (Venus / Jupiter karaka)",
            verdict="neutral",
            detail=(
                "The relationship significators carry across from birth to navamsha "
                "without collapse — comfort and warmth in marriage are workable, "
                "shaped by how each significator is placed below."
            ),
            why="; ".join(kn),
            chapter="D9 Ch.2 (marriage quality)",
        ))

    # --- D1 -> D9 trajectory ---
    traj = nav.get("trajectory", [])
    if traj:
        out.append(RuleFinding(
            topic="Life trajectory (how strength shifts D1 → D9)",
            verdict="info",
            detail=(
                "Some planets change dignity between the birth chart and the navamsha, "
                "which is the classic signal of how life direction matures over time."
            ),
            why="; ".join(traj[:3]),
            chapter="D9 Ch.2 (D1↔D9 trajectory)",
        ))

    # --- Separation / divorce indicators ---
    out.append(_simple(
        nav, "separation",
        topic="Separation / distance in marriage",
        favourable="No strong separation pattern on the navamsha 7th-lord or 4th axis.",
        caution_lead="The 7th-lord / 4th-house axis carries a separation signal — ",
        chapter="D9 Ch.2 (separation)",
    ))

    # --- Spouse longevity / mangalya ---
    mang = nav.get("mangalya_note", "")
    if mang:
        out.append(RuleFinding(
            topic="Spouse well-being (mangalya study flag)",
            verdict="caution",
            detail=(
                "The navamsha 8th carries a malefic load. This is a study-only caution "
                "in the classics — best handled with care for the partner's health and "
                "honest, calm conduct, not alarm."
            ),
            highlight=True,
            why=mang,
            chapter="D9 Ch.2 (spouse longevity)",
        ))
    else:
        out.append(RuleFinding(
            topic="Spouse well-being (mangalya study flag)",
            verdict="favourable",
            detail="No heavy malefic cluster on the navamsha 8th — no mangalya caution.",
            chapter="D9 Ch.2 (spouse longevity)",
        ))

    # --- Multiple relationships / affairs (Ch.4) ---
    multi = nav.get("multiple_signals", [])
    if multi:
        out.append(RuleFinding(
            topic="Multiple-relationship signals",
            verdict="caution",
            detail=(
                "There are placements the author links to more than one significant "
                "relationship or restlessness in partnership. Read it as a call for "
                "clarity and loyalty rather than a verdict."
            ),
            highlight=True,
            why="; ".join(multi[:2]),
            chapter="D9 Ch.4 (multiple relations)",
        ))
    if nav.get("sexual_urge"):
        out.append(RuleFinding(
            topic="Mars–Venus drive (Ch.4 example)",
            verdict="neutral",
            detail=(
                "Mars and Venus sit together (or face off) in the navamsha — the book's "
                "marker of strong physical magnetism and a passionate temperament in "
                "relationships."
            ),
            highlight=True,
            why=nav.get("sexual_note", ""),
            chapter="D9 Ch.4 (Mars-Venus)",
        ))

    # --- Foreign / cross-community marriage ---
    dkf = nav.get("dk_foreign", [])
    if dkf:
        out.append(RuleFinding(
            topic="Foreign / cross-community partner",
            verdict="info",
            detail=(
                "The darakaraka (deepest spouse significator) hints at a partner from a "
                "different place, community, or background — a flavour, not a guarantee."
            ),
            why="; ".join(dkf[:2]),
            chapter="D9 Ch.2/4 (foreign marriage)",
        ))

    # --- Devotion / dharma / religion ---
    spir = nav.get("spiritual_signals", [])
    if spir:
        out.append(RuleFinding(
            topic="Devotion & dharma",
            verdict="favourable",
            detail=(
                "The navamsha's faith houses are active — a natural pull toward "
                "devotion, philosophy, or inner practice that deepens with age."
            ),
            why="; ".join(spir[:2]),
            chapter="D9 Ch.8 (devotion)",
        ))

    # --- Marriage timing windows ---
    win = nav.get("marriage_windows", [])
    if win:
        first = win[0]
        out.append(RuleFinding(
            topic="Marriage / partnership timing",
            verdict="info",
            detail=(
                f"Periods ruled by the marriage significators are the natural windows "
                f"for partnership to ripen — the nearest being {first.get('lord','')} "
                f"({first.get('range','')})."
            ),
            why="; ".join(f"{w.get('lord','')} {w.get('range','')}" for w in win[:3]),
            chapter="D9 Ch.5 (timing)",
        ))

    return out


# ----------------------------------------------------------------------------
# Generic inspector for D1-D7 (shared, book-grounded Parashari/Goel rules)
# ----------------------------------------------------------------------------
from astro_precompute import get_dignity  # noqa: E402

# signature house + plain topic each varga is read for
_VARGA_SIGNATURE = {
    "D1": (1, "your body, vitality and overall direction"),
    "D2": (2, "wealth, savings and family resources"),
    "D3": (3, "courage, drive and relations with siblings"),
    "D4": (4, "home, property and peace of mind"),
    "D7": (5, "children and progeny"),
}
_VARGA_KARAKA_LOCAL = {
    "D1": "", "D2": "Jupiter", "D3": "Mars", "D4": "Moon", "D7": "Jupiter",
}
_VARGA_KARAKA_TOPIC = {
    "D2": "wealth", "D3": "courage and siblings", "D4": "comfort and mother",
    "D7": "children",
}

# Higher vargas (D10-D60) draw their config from the book corpus so the maps
# stay in one place. Merge those entries in at import time.
try:
    from divisional_book_corpus import HIGHER_VARGA_CORPUS as _HVC
    for _v, _c in _HVC.items():
        _VARGA_SIGNATURE.setdefault(
            _v, (_c.get("signature_house", 1), _c.get("theme", "this area of life"))
        )
        _VARGA_KARAKA_LOCAL.setdefault(_v, _c.get("karaka", ""))
        _VARGA_KARAKA_TOPIC.setdefault(_v, _c.get("karaka_topic", _c.get("theme", "")))
except Exception:  # noqa: BLE001 - corpus optional at import
    pass
_KENDRA_TRIKONA = {1, 4, 5, 7, 9, 10}
_STRONG_DIG = {"exalted", "own_sign", "moolatrikona"}
_WEAK_DIG = {"debilitated", "enemy_sign"}
_MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
_BENEFICS = {"Moon", "Mercury", "Jupiter", "Venus"}


def _dig_word(dig: str) -> str:
    return {
        "exalted": "exalted", "own_sign": "in its own sign",
        "moolatrikona": "in moolatrikona", "great_friend_sign": "well supported",
        "friendly": "in a friendly sign", "neutral_sign": "in a neutral sign",
        "neutral": "in a neutral sign", "enemy_sign": "in an enemy sign",
        "debilitated": "debilitated",
    }.get(dig, dig or "unknown")


def inspect_varga_generic(varga: str, chart: dict, pc: dict) -> list[RuleFinding]:
    """Book-grounded findings shared across D1-D7.

    Uses only standard Parashari/Goel rules each chapter states and proves with
    examples: vargottama, varga-lagna-lord placement, karaka dignity, key-house
    occupants, and the 'house lord in 6/8/12 spoils that house' rule.
    """
    out: list[RuleFinding] = []
    varga = varga.upper()
    planets = chart.get("planets", {})
    houses = chart.get("houses", {})
    v_lagna = chart.get("lagna", "")
    sig_house, sig_topic = _VARGA_SIGNATURE.get(varga, (1, "this area of life"))

    def dig_of(p: str) -> str:
        b = planets.get(p, {})
        return get_dignity(p, b.get("sign", "")) if b.get("sign") else "unknown"

    # --- Vargottama planets (author-emphasised strength) ---
    # Meaningless for D1 (the rashi chart compares to itself), so skip there.
    vgt = [] if varga == "D1" else [
        p for p, b in planets.items()
        if b.get("d1_sign") and b.get("d1_sign") == b.get("sign")
    ]
    if varga != "D1" and (chart.get("vargottama_lagna") or (v_lagna and v_lagna == chart.get("d1_lagna"))):
        vgt = ["the ascendant"] + vgt
    if vgt:
        out.append(RuleFinding(
            topic="Vargottama (repeats sign in D1 & this chart)",
            verdict="favourable",
            detail=(
                f"{_join(vgt)} {_v(vgt, 'holds', 'hold')} the same sign here as in the "
                f"birth chart. The author treats vargottama as a seal of strength — "
                f"what these significations promise tends to actually materialise."
            ),
            highlight=True,
            why=f"Vargottama: {', '.join(str(x) for x in vgt)}",
            chapter=f"{varga} Ch.1 (vargottama)",
        ))

    # --- Varga lagna lord placement ---
    ll = chart.get("lagna_lord", "")
    ll_h = chart.get("lagna_lord_varga_house") or planets.get(ll, {}).get("house")
    ll_dig = chart.get("lagna_lord_dignity_varga", "") or dig_of(ll)
    if ll and ll_h:
        if ll_h in (6, 8, 12):
            out.append(RuleFinding(
                topic=f"Ascendant lord of the {varga} chart",
                verdict="caution",
                detail=(
                    f"The ruler of this chart, {ll}, sits in its {_ord(ll_h)} house — a "
                    f"testing spot. It means the headline matters of {sig_topic} ask for "
                    f"sustained effort before they settle."
                ),
                highlight=True,
                why=f"{varga} lagna lord {ll} in H{ll_h}, {_dig_word(ll_dig)}",
                chapter=f"{varga} (lagna-lord strength)",
            ))
        elif ll_h in _KENDRA_TRIKONA or ll_dig in _STRONG_DIG:
            out.append(RuleFinding(
                topic=f"Ascendant lord of the {varga} chart",
                verdict="favourable",
                detail=(
                    f"The ruler of this chart, {ll}, is well placed in its {_ord(ll_h)} "
                    f"house ({_dig_word(ll_dig)}). The foundation of {sig_topic} is sound "
                    f"and supports the rest of the reading."
                ),
                why=f"{varga} lagna lord {ll} in H{ll_h}, {_dig_word(ll_dig)}",
                chapter=f"{varga} (lagna-lord strength)",
            ))

    # --- Karaka of the varga ---
    karaka = _VARGA_KARAKA_LOCAL.get(varga, "")
    kb = planets.get(karaka, {}) if karaka else {}
    if karaka and kb:
        kh = kb.get("house")
        kdig = dig_of(karaka)
        ktopic = _VARGA_KARAKA_TOPIC.get(varga, sig_topic)
        # Dignity takes priority: a debilitated/enemy karaka is a caution even in
        # an angle; angularity alone (with non-weak dignity) is favourable.
        if kdig in _WEAK_DIG or kh in (6, 8, 12):
            relief = (
                f" It does sit in a strong {_ord(kh)} house, which softens the strain."
                if kh in _KENDRA_TRIKONA else ""
            )
            out.append(RuleFinding(
                topic=f"{karaka} — natural significator of {ktopic}",
                verdict="caution",
                detail=(
                    f"{karaka}, the significator of {ktopic}, is under pressure here "
                    f"({_dig_word(kdig)}, house {kh}), so the author reads {ktopic} as "
                    f"coming with delay or extra care — strengthening {karaka} helps.{relief}"
                ),
                highlight=True,
                why=f"{karaka} in H{kh}, {_dig_word(kdig)}",
                chapter=f"{varga} (karaka rule)",
            ))
        elif kdig in _STRONG_DIG or kh in _KENDRA_TRIKONA:
            out.append(RuleFinding(
                topic=f"{karaka} — natural significator of {ktopic}",
                verdict="favourable",
                detail=(
                    f"{karaka}, which carries {ktopic}, is well placed here "
                    f"({_dig_word(kdig)}, house {kh}). This is the single best "
                    f"confirmation the chart can give for {ktopic}."
                ),
                highlight=True,
                why=f"{karaka} in H{kh}, {_dig_word(kdig)}",
                chapter=f"{varga} (karaka rule)",
            ))

    # --- Key (signature) house occupants ---
    sig = houses.get(sig_house) or houses.get(str(sig_house)) or {}
    tenants = sig.get("tenants", [])
    if tenants:
        mal = [t for t in tenants if t in _MALEFICS]
        ben = [t for t in tenants if t in _BENEFICS]
        if ben and not mal:
            out.append(RuleFinding(
                topic=f"The {_ord(sig_house)} house — heart of this chart",
                verdict="favourable",
                detail=(
                    f"{_join(ben)} {_v(ben, 'sits', 'sit')} in the {_ord(sig_house)} house, "
                    f"the seat of {sig_topic}. A benefic here is exactly what the book "
                    f"wants to see — a protected, well-supported area."
                ),
                highlight=True,
                why=f"H{sig_house} tenants: {', '.join(tenants)}",
                chapter=f"{varga} (signature house)",
            ))
        elif mal and not ben:
            out.append(RuleFinding(
                topic=f"The {_ord(sig_house)} house — heart of this chart",
                verdict="caution",
                detail=(
                    f"{_join(mal)} {_v(mal, 'sits', 'sit')} in the {_ord(sig_house)} house "
                    f"of {sig_topic}. Malefics here add friction — results come, but "
                    f"through grit and the occasional setback."
                ),
                highlight=True,
                why=f"H{sig_house} tenants: {', '.join(tenants)}",
                chapter=f"{varga} (signature house)",
            ))
        else:
            out.append(RuleFinding(
                topic=f"The {_ord(sig_house)} house — heart of this chart",
                verdict="neutral",
                detail=(
                    f"The {_ord(sig_house)} house of {sig_topic} holds {_join(tenants)} — "
                    f"a mix of supportive and testing influences that balance out."
                ),
                why=f"H{sig_house} tenants: {', '.join(tenants)}",
                chapter=f"{varga} (signature house)",
            ))

    # --- House lord in 6/8/12 spoils that house (Parashari, varga-internal) ---
    spoiled = []
    for h in range(1, 13):
        hrec = houses.get(h) or houses.get(str(h)) or {}
        lord = hrec.get("lord", "")
        lb = planets.get(lord, {})
        lh = lb.get("house")
        if lh in (6, 8, 12) and lord:
            spoiled.append((h, lord, lh))
    # only surface if the signature house itself is spoiled, else summarise
    sig_spoiled = [s for s in spoiled if s[0] == sig_house]
    if sig_spoiled:
        _, lord, lh = sig_spoiled[0]
        out.append(RuleFinding(
            topic=f"Lord of the {_ord(sig_house)} house weakened",
            verdict="caution",
            detail=(
                f"The ruler of the {_ord(sig_house)} house ({lord}) slips into its "
                f"{_ord(lh)} house — the classic 'house lord in a difficult house' rule. "
                f"It dilutes {sig_topic} and asks for patience."
            ),
            highlight=True,
            why=f"H{sig_house} lord {lord} in H{lh}",
            chapter=f"{varga} (house-lord placement)",
        ))
    elif len(spoiled) >= 4:
        areas = ", ".join(f"{_ord(h)}" for h, _, _ in spoiled[:4])
        out.append(RuleFinding(
            topic="Several house lords in difficult houses",
            verdict="neutral",
            detail=(
                f"A few life-area rulers ({areas}) fall into 6/8/12 here. It is common "
                f"and simply flags where this chart asks for extra effort over time."
            ),
            why="; ".join(f"H{h} lord {l} in H{x}" for h, l, x in spoiled[:5]),
            chapter=f"{varga} (house-lord placement)",
        ))

    return out


def _simple(nav: dict, key: str, topic: str, favourable: str,
            caution_lead: str, chapter: str) -> RuleFinding:
    """Build a finding from a separation-style derived field if present."""
    lord7 = nav.get("lord7_d9", "")
    l7h = None
    for p, e in (nav.get("d9_enriched") or {}).items():
        if p == lord7:
            l7h = e.get("d9_house")
    d9h = nav.get("d9_houses") or {}
    fourth = d9h.get(4) or d9h.get("4")
    if l7h in (6, 8, 12) or (fourth and fourth.strip()):
        detail = caution_lead + (
            f"the 7th lord {lord7} sits in house {l7h}. "
            if l7h in (6, 8, 12) else "the 4th (domestic peace) is activated. "
        ) + "Steady communication and patience keep the bond on track."
        return RuleFinding(topic=topic, verdict="caution", detail=detail,
                           highlight=l7h in (6, 8, 12), why=f"7th lord {lord7} H{l7h}",
                           chapter=chapter)
    return RuleFinding(topic=topic, verdict="favourable", detail=favourable,
                       chapter=chapter)


# ----------------------------------------------------------------------------
# Special (chart-specific classical) inspectors for D24, D27, D30, D60
# ----------------------------------------------------------------------------

# D30 Trimshamsha: the planet ruling the portion (= lord of the D30 sign) tells
# the nature of misfortune. Benefic rulers protect; malefic rulers intensify.
_TRIMSHA_NATURE = {
    "Mars": ("caution", "accidents, cuts or surgery, fevers, and trouble born of haste or anger"),
    "Saturn": ("caution", "slow-building hardship — chronic strain, delays, sorrow, and overwork"),
    "Jupiter": ("favourable", "strong protection — misfortune is cushioned by good fortune, ethics and wisdom"),
    "Mercury": ("favourable", "mostly minor, manageable troubles that your intelligence resolves"),
    "Venus": ("favourable", "comfort- and relationship-related ups and downs, generally mild"),
}

# D60 Shashtiamsha deity names + benefic(soumya)/malefic(kroora) nature (BPHS).
_SHASHTI_NAMES = [
    "Ghora", "Rakshasa", "Deva", "Kubera", "Yaksha", "Kinnara", "Bhrashta", "Kulaghna",
    "Garala", "Vahni", "Maya", "Purishaka", "Apampati", "Marut", "Kaala", "Sarpa",
    "Amrita", "Indu", "Mridu", "Komala", "Heramba", "Brahma", "Vishnu", "Maheshwara",
    "Deva", "Ardra", "Kalinasha", "Kshitisha", "Kamalakara", "Gulika", "Mrityu", "Kaala",
    "Davagni", "Ghora", "Yama", "Kantaka", "Sudha", "Amrita", "Purnachandra", "Vishadagdha",
    "Kulanasha", "Vamsakshaya", "Utpata", "Kaala", "Saumya", "Komala", "Sheetala",
    "Karaladamshtra", "Chandramukhi", "Praveena", "Kalagni", "Dandayudha", "Nirmala",
    "Saumya", "Kroora", "Atisheetala", "Amrita", "Payodhi", "Bhramana", "Chandrarekha",
]
_SHASHTI_KROORA = {0, 1, 7, 8, 9, 10, 11, 14, 15, 29, 30, 31, 32, 33, 34, 39, 41, 42, 43, 47, 50, 51, 58}


def _shashti_index(deg_in_sign: float) -> int:
    return max(0, min(59, int(float(deg_in_sign) * 2)))


def inspect_d24(d24: dict, pc: dict, _nav=None) -> list[RuleFinding]:
    """Education special checks — intellect karakas, formal-education axis, exams."""
    out: list[RuleFinding] = []
    planets = d24.get("planets", {})

    def dig(p):
        b = planets.get(p, {})
        return get_dignity(p, b.get("sign", "")) if b.get("sign") else "unknown"

    merc, jup = planets.get("Mercury", {}), planets.get("Jupiter", {})
    if merc and jup:
        m_ok = dig("Mercury") in _STRONG_DIG or merc.get("house") in _KENDRA_TRIKONA
        j_ok = dig("Jupiter") in _STRONG_DIG or jup.get("house") in _KENDRA_TRIKONA
        conj = merc.get("sign") == jup.get("sign")
        if conj or (m_ok and j_ok):
            out.append(RuleFinding(
                topic="Mercury–Jupiter — the scholar's combination",
                verdict="favourable",
                detail=(
                    "Mercury (sharp intellect) and Jupiter (deep wisdom) are both working "
                    "well in your education chart"
                    + (" and share a sign" if conj else "")
                    + " — the classic signature of genuine scholarship, with the patience "
                    "to master a subject, not just pass it."
                ),
                highlight=True,
                why=f"Mercury {dig('Mercury')} H{merc.get('house')}; Jupiter {dig('Jupiter')} H{jup.get('house')}"
                    + ("; conjunct" if conj else ""),
                chapter="D24 (intellect karakas)",
            ))
        elif dig("Mercury") in _WEAK_DIG and dig("Jupiter") in _WEAK_DIG:
            out.append(RuleFinding(
                topic="Mercury–Jupiter — the scholar's combination",
                verdict="caution",
                detail=(
                    "Both intellect significators (Mercury and Jupiter) are under pressure "
                    "in the education chart. Learning rewards a slower, well-supported "
                    "approach here — tutoring, structure, and revisiting basics pay off."
                ),
                highlight=True,
                why=f"Mercury {dig('Mercury')}; Jupiter {dig('Jupiter')}",
                chapter="D24 (intellect karakas)",
            ))

    # Formal-education axis: 4th house (schooling) tenants/lord
    houses = d24.get("houses", {})
    fourth = houses.get(4, {})
    f_tenants = fourth.get("tenants", [])
    fmal = [t for t in f_tenants if t in _MALEFICS and t not in ("Sun",)]
    if {"Saturn", "Rahu", "Ketu"} & set(f_tenants):
        out.append(RuleFinding(
            topic="Formal schooling (4th house)",
            verdict="caution",
            detail=(
                "A heavy planet sits on the schooling house — education may face an "
                "interruption, a change of institution, or a late bloom. Persistence "
                "turns this into depth rather than a dead end."
            ),
            highlight=True,
            why=f"D24 4th tenants: {', '.join(f_tenants)}",
            chapter="D24 (formal education)",
        ))
    elif any(t in _BENEFICS for t in f_tenants):
        out.append(RuleFinding(
            topic="Formal schooling (4th house)",
            verdict="favourable",
            detail=(
                "A benefic graces the schooling house — a smooth, well-supported formal "
                "education with the comfort to study without major disruption."
            ),
            highlight=True,
            why=f"D24 4th tenants: {', '.join(f_tenants)}",
            chapter="D24 (formal education)",
        ))

    # Competitive exams / authority through degrees — Sun strength
    sun = planets.get("Sun", {})
    if sun and (dig("Sun") in _STRONG_DIG or sun.get("house") in (1, 9, 10)):
        out.append(RuleFinding(
            topic="Competitive exams & recognised qualifications",
            verdict="favourable",
            detail=(
                "The Sun is well placed in the learning chart — a good sign for success "
                "in competitive exams and for qualifications that carry authority and "
                "recognition."
            ),
            why=f"Sun {dig('Sun')} H{sun.get('house')}",
            chapter="D24 (Sun / recognition)",
        ))
    return out


def inspect_d27(d27: dict, pc: dict, _nav=None) -> list[RuleFinding]:
    """Strength special checks — physical vitality, mental resilience, weak points."""
    out: list[RuleFinding] = []
    planets = d27.get("planets", {})

    def dig(p):
        b = planets.get(p, {})
        return get_dignity(p, b.get("sign", "")) if b.get("sign") else "unknown"

    # Physical vitality — Mars + Sun
    mars, sun = planets.get("Mars", {}), planets.get("Sun", {})
    m_strong = dig("Mars") in _STRONG_DIG or mars.get("house") in _KENDRA_TRIKONA
    s_strong = dig("Sun") in _STRONG_DIG or sun.get("house") in _KENDRA_TRIKONA
    m_weak = dig("Mars") in _WEAK_DIG or mars.get("house") in (6, 8, 12)
    s_weak = dig("Sun") in _WEAK_DIG or sun.get("house") in (6, 8, 12)
    if m_strong and s_strong:
        out.append(RuleFinding(
            topic="Physical vitality (Mars & Sun)",
            verdict="favourable",
            detail=(
                "Both vitality planets — Mars (raw strength) and the Sun (life-force) — "
                "are strong here. You have a robust constitution and bounce back quickly "
                "from physical strain."
            ),
            highlight=True,
            why=f"Mars {dig('Mars')} H{mars.get('house')}; Sun {dig('Sun')} H{sun.get('house')}",
            chapter="D27 (vitality karakas)",
        ))
    elif m_weak and s_weak:
        out.append(RuleFinding(
            topic="Physical vitality (Mars & Sun)",
            verdict="caution",
            detail=(
                "Both vitality planets are under pressure — stamina can run low and "
                "recovery is slower. Regular exercise, rest, and not over-spending energy "
                "make a real difference for you."
            ),
            highlight=True,
            why=f"Mars {dig('Mars')} H{mars.get('house')}; Sun {dig('Sun')} H{sun.get('house')}",
            chapter="D27 (vitality karakas)",
        ))

    # Mental resilience — Moon
    moon = planets.get("Moon", {})
    if moon:
        if dig("Moon") in _WEAK_DIG or moon.get("house") in (6, 8, 12):
            out.append(RuleFinding(
                topic="Mental resilience (Moon)",
                verdict="caution",
                detail=(
                    "The Moon is stressed in the strength chart — the mind tires or worries "
                    "under sustained pressure. Steady routine, calm surroundings, and good "
                    "sleep protect your mental stamina."
                ),
                highlight=True,
                why=f"Moon {dig('Moon')} H{moon.get('house')}",
                chapter="D27 (mental strength)",
            ))
        elif dig("Moon") in _STRONG_DIG or moon.get("house") in _KENDRA_TRIKONA:
            out.append(RuleFinding(
                topic="Mental resilience (Moon)",
                verdict="favourable",
                detail=(
                    "A strong Moon gives steady nerves — you hold composure under pressure "
                    "and recover emotionally with resilience."
                ),
                why=f"Moon {dig('Moon')} H{moon.get('house')}",
                chapter="D27 (mental strength)",
            ))

    # Weak points — malefic cluster in 6/8/12
    drain = [p for p, b in planets.items() if b.get("house") in (6, 8, 12) and p in _MALEFICS]
    if len(drain) >= 2:
        out.append(RuleFinding(
            topic="Where energy is tested (6th/8th/12th load)",
            verdict="caution",
            detail=(
                f"{_join(drain)} gather in the testing houses of the strength chart — these "
                f"mark where your energy is most easily drained. Treat them as the areas to "
                f"guard with rest and care."
            ),
            highlight=True,
            why=f"Malefics in 6/8/12: {', '.join(drain)}",
            chapter="D27 (weak points)",
        ))
    return out


def inspect_d30(d30: dict, pc: dict, _nav=None) -> list[RuleFinding]:
    """Misfortune special checks — Trimshamsha lord of lagna and Moon (classical)."""
    out: list[RuleFinding] = []
    planets = d30.get("planets", {})

    # Trimshamsha lord of the ascendant = lord of the D30 lagna sign.
    lagna_lord = SIGN_LORD.get(d30.get("lagna", ""), "")
    nature = _TRIMSHA_NATURE.get(lagna_lord)
    if nature:
        verdict, desc = nature
        out.append(RuleFinding(
            topic="Trimshamsha lord of the ascendant (nature of troubles)",
            verdict=verdict,
            detail=(
                f"Your ascendant in the misfortune chart is ruled by {lagna_lord}, so the "
                f"classics read the texture of life's difficulties as {desc}. "
                + ("This is a protective ruler — read it as reassurance."
                   if verdict == "favourable" else
                   "Forewarned is forearmed: simple care in this area defuses most of it.")
            ),
            highlight=True,
            why=f"D30 lagna {d30.get('lagna','')} ruled by {lagna_lord}",
            chapter="D30 (Trimshamsha lord — classical)",
        ))

    # Trimshamsha lord of the Moon = source of emotional/health troubles.
    moon = planets.get("Moon", {})
    moon_lord = SIGN_LORD.get(moon.get("sign", ""), "")
    nat_m = _TRIMSHA_NATURE.get(moon_lord)
    if nat_m and moon_lord != lagna_lord:
        verdict, desc = nat_m
        out.append(RuleFinding(
            topic="Trimshamsha lord of the Moon (mind & well-being)",
            verdict=verdict,
            detail=(
                f"The Moon's portion is ruled by {moon_lord}, pointing to {desc} on the "
                f"emotional and health side. "
                + ("A gentle ruler — the mind stays largely protected."
                   if verdict == "favourable" else
                   "Mind your stress and health habits and this stays well managed.")
            ),
            highlight=True,
            why=f"Moon D30 sign {moon.get('sign','')} ruled by {moon_lord}",
            chapter="D30 (Trimshamsha lord — classical)",
        ))
    return out


def inspect_d60(d60: dict, pc: dict, _nav=None) -> list[RuleFinding]:
    """Past-karma special checks — Shashtiamsha deity of lagna & planets (classical)."""
    out: list[RuleFinding] = []
    meta = pc.get("meta", {})
    planets_pc = pc.get("planets", {})

    # Ascendant shashtiamsha deity — overall past-life merit.
    try:
        lagna_deg = float(meta.get("lagna_degree") or pc.get("lagna", {}).get("degree_in_sign") or 0)
    except (TypeError, ValueError):
        lagna_deg = 0.0
    li = _shashti_index(lagna_deg)
    lname = _SHASHTI_NAMES[li]
    lkroora = li in _SHASHTI_KROORA
    out.append(RuleFinding(
        topic="Ascendant Shashtiamsha (the karmic seed of this life)",
        verdict="caution" if lkroora else "favourable",
        detail=(
            f"Your ascendant falls in the <em>{lname}</em> shashtiamsha — a "
            + ("difficult (krura) portion. The classics read it as karmic debt to work "
               "through with honest effort; it explains early friction that eases as you "
               "settle accounts."
               if lkroora else
               "benefic (saumya) portion. This is among the most reassuring signs the chart "
               "gives — a store of past-life merit quietly supporting this life.")
        ),
        highlight=True,
        why=f"Lagna shashtiamsha #{li + 1} ({lname}) — {'krura' if lkroora else 'saumya'}",
        chapter="D60 (Shashtiamsha deity — classical)",
    ))

    # Karmic balance across planets, and flag any key planet in a harsh amsha.
    good, harsh = [], []
    for name in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"):
        pl = planets_pc.get(name, {})
        if not pl.get("sign"):
            continue
        idx = _shashti_index(pl.get("degree_in_sign") or 0)
        (harsh if idx in _SHASHTI_KROORA else good).append((name, _SHASHTI_NAMES[idx]))
    if good or harsh:
        out.append(RuleFinding(
            topic="Karmic balance across your planets",
            verdict="favourable" if len(good) >= len(harsh) else "neutral",
            detail=(
                f"Weighing every planet by its shashtiamsha, {len(good)} fall in benefic "
                f"portions and {len(harsh)} in harsher ones. "
                + ("The benefic side carries the day — past merit outweighs past debt."
                   if len(good) >= len(harsh) else
                   "It is a mixed ledger — some accounts are still being settled, which is "
                   "normal and workable.")
            ),
            why="benefic: " + ", ".join(f"{n}({d})" for n, d in good[:4])
                + (" · harsh: " + ", ".join(f"{n}({d})" for n, d in harsh[:4]) if harsh else ""),
            chapter="D60 (Shashtiamsha — classical)",
        ))
    # Highlight a key planet in a notably harsh deity (Ghora/Rakshasa/Mrityu/Kaala/Yama).
    severe = {"Ghora", "Rakshasa", "Mrityu", "Kaala", "Yama", "Garala", "Sarpa", "Kulaghna", "Kulanasha"}
    for name in ("Sun", "Moon", "Jupiter", "Venus"):
        pl = planets_pc.get(name, {})
        if not pl.get("sign"):
            continue
        idx = _shashti_index(pl.get("degree_in_sign") or 0)
        nm = _SHASHTI_NAMES[idx]
        if nm in severe and idx in _SHASHTI_KROORA:
            out.append(RuleFinding(
                topic=f"{name} in a karmically heavy portion ({nm})",
                verdict="caution",
                detail=(
                    f"{name} sits in the <em>{nm}</em> shashtiamsha — a portion the classics "
                    f"weight heavily. What {name} signifies carries a karmic lesson best met "
                    f"with patience and integrity; handled well, it becomes a source of depth."
                ),
                highlight=True,
                why=f"{name} shashtiamsha #{idx + 1} ({nm})",
                chapter="D60 (Shashtiamsha deity — classical)",
            ))
            break
    return out


def _dig_local(planets: dict, p: str) -> str:
    b = planets.get(p, {})
    return get_dignity(p, b.get("sign", "")) if b.get("sign") else "unknown"


def inspect_d10(d10: dict, pc: dict, _nav=None) -> list[RuleFinding]:
    """Career special checks — Raja-yoga of the 10th, Panch Mahapurusha, fall yoga."""
    out: list[RuleFinding] = []
    planets = d10.get("planets", {})
    houses = d10.get("houses", {})
    v_lagna = d10.get("lagna", "")

    # 10th lord placement — the engine of professional rise.
    tenth = houses.get(10, {})
    tenth_lord = tenth.get("lord", "")
    tl = planets.get(tenth_lord, {})
    tl_h = tl.get("house")
    tl_dig = _dig_local(planets, tenth_lord)
    if tl_h in _KENDRA_TRIKONA or tl_dig in _STRONG_DIG:
        out.append(RuleFinding(
            topic="The career lord well placed (rise yoga)",
            verdict="favourable",
            detail=(
                f"The ruler of your profession ({tenth_lord}) is strongly placed "
                f"({_dig_word(tl_dig)}, house {tl_h}). This is the engine of a steady "
                f"climb — authority and recognition build through your own competence."
            ),
            highlight=True,
            why=f"D10 10th lord {tenth_lord} in H{tl_h}, {_dig_word(tl_dig)}",
            chapter="D10 (career-lord strength)",
        ))
    elif tl_h in (6, 8, 12) or tl_dig in _WEAK_DIG:
        out.append(RuleFinding(
            topic="The career lord under pressure (fall yoga)",
            verdict="caution",
            detail=(
                f"The ruler of your profession ({tenth_lord}) is placed in a testing spot "
                f"({_dig_word(tl_dig)}, house {tl_h}). Expect a non-linear career — periods "
                f"of setback or change that, handled patiently, lead to reinvention."
            ),
            highlight=True,
            why=f"D10 10th lord {tenth_lord} in H{tl_h}, {_dig_word(tl_dig)}",
            chapter="D10 (career-lord strength)",
        ))

    # Panch Mahapurusha — a non-luminary in own/exalted sign in a kendra of D10.
    PMP = {"Mars": "Ruchaka", "Mercury": "Bhadra", "Jupiter": "Hamsa",
           "Venus": "Malavya", "Saturn": "Sasa"}
    for pl, yoga in PMP.items():
        b = planets.get(pl, {})
        if not b:
            continue
        if _dig_local(planets, pl) in ("exalted", "own_sign", "moolatrikona") and b.get("house") in (1, 4, 7, 10):
            out.append(RuleFinding(
                topic=f"{yoga} Yoga — a distinguished-career signature",
                verdict="favourable",
                detail=(
                    f"{pl} stands strong in an angle of your career chart, forming "
                    f"{yoga} Yoga — a classical mark of someone who rises above the ordinary "
                    f"in their field and is remembered for their work."
                ),
                highlight=True,
                why=f"{pl} {_dig_word(_dig_local(planets, pl))} in H{b.get('house')} (kendra)",
                chapter="D10 (Panch Mahapurusha)",
            ))
            break

    # Sun in the 10th — authority / government / leadership.
    sun = planets.get("Sun", {})
    if sun.get("house") == 10:
        out.append(RuleFinding(
            topic="Sun on the career summit",
            verdict="favourable",
            detail=(
                "The Sun sits at the very top of your career chart — a strong pull toward "
                "authority, leadership, government or a role where you are clearly in charge."
            ),
            highlight=True,
            why="Sun in D10 H10",
            chapter="D10 (Sun / authority)",
        ))
    return out


def inspect_d12(d12: dict, pc: dict, _nav=None) -> list[RuleFinding]:
    """Parental well-being special checks — mother (4th/Moon) and father (9th/Sun)."""
    out: list[RuleFinding] = []
    planets = d12.get("planets", {})
    houses = d12.get("houses", {})

    def parent_check(house_n, karaka, label, topic):
        hrec = houses.get(house_n, {})
        tenants = hrec.get("tenants", [])
        lord = hrec.get("lord", "")
        lord_h = planets.get(lord, {}).get("house")
        kdig = _dig_local(planets, karaka)
        mal = [t for t in tenants if t in _MALEFICS]
        strain = bool(mal) or kdig in _WEAK_DIG or lord_h in (6, 8, 12)
        if strain:
            out.append(RuleFinding(
                topic=topic,
                verdict="caution",
                detail=(
                    f"The {label} axis carries some strain in the lineage chart — read it as "
                    f"a reminder to look after your {label}'s health and to nurture the bond, "
                    f"not as a prediction of loss."
                ),
                highlight=True,
                why=f"D12 H{house_n} tenants {tenants or 'empty'}; {karaka} {kdig}; lord {lord} H{lord_h}",
                chapter=f"D12 ({label} axis)",
            ))
        elif kdig in _STRONG_DIG or any(t in _BENEFICS for t in tenants):
            out.append(RuleFinding(
                topic=topic,
                verdict="favourable",
                detail=(
                    f"The {label} axis is well supported — a warm, lasting bond and good "
                    f"blessings carried from your {label}'s side."
                ),
                highlight=True,
                why=f"D12 H{house_n} tenants {tenants or 'empty'}; {karaka} {kdig}",
                chapter=f"D12 ({label} axis)",
            ))
        else:
            out.append(RuleFinding(
                topic=topic,
                verdict="neutral",
                detail=(
                    f"The {label} axis is steady — no strong blessing and no real strain. "
                    f"The bond rests largely on everyday care and the dasha periods that "
                    f"activate {label}-related houses."
                ),
                why=f"D12 H{house_n} tenants {tenants or 'empty'}; {karaka} {kdig}; lord {lord} H{lord_h}",
                chapter=f"D12 ({label} axis)",
            ))

    parent_check(4, "Moon", "mother", "Mother — bond & well-being")
    parent_check(9, "Sun", "father", "Father — bond & well-being")
    return out


def inspect_d16(d16: dict, pc: dict, _nav=None) -> list[RuleFinding]:
    """Vehicles & comfort special checks — 4th house and Venus; accident caution."""
    out: list[RuleFinding] = []
    planets = d16.get("planets", {})
    houses = d16.get("houses", {})
    fourth = houses.get(4, {})
    tenants = fourth.get("tenants", [])
    venus = planets.get("Venus", {})
    vdig = _dig_local(planets, "Venus")

    harsh = [t for t in tenants if t in ("Mars", "Saturn", "Rahu", "Ketu")]
    if harsh:
        out.append(RuleFinding(
            topic="Vehicles & the comfort house (accident caution)",
            verdict="caution",
            detail=(
                f"{_join(harsh)} {_v(harsh, 'sits', 'sit')} on the vehicle-and-comfort house. "
                f"The classics read this as a need for care with vehicles — maintenance, "
                f"safe driving, and not over-spending on luxuries that strain you."
            ),
            highlight=True,
            why=f"D16 4th tenants: {', '.join(tenants)}",
            chapter="D16 (vehicles / 4th)",
        ))
    elif any(t in _BENEFICS for t in tenants) or vdig in _STRONG_DIG:
        out.append(RuleFinding(
            topic="Vehicles & comforts well supported",
            verdict="favourable",
            detail=(
                "Your comfort house is gently supported — good, trouble-free vehicles and "
                "an easy enjoyment of life's luxuries are indicated."
            ),
            highlight=True,
            why=f"D16 4th tenants {tenants or 'empty'}; Venus {vdig}",
            chapter="D16 (vehicles / Venus)",
        ))
    if venus and (vdig in _WEAK_DIG or venus.get("house") in (6, 8, 12)):
        out.append(RuleFinding(
            topic="Venus — significator of luxuries",
            verdict="caution",
            detail=(
                "Venus, the giver of comforts, is under pressure here — luxuries may come "
                "later or cost more effort. Quality over quantity serves you better."
            ),
            why=f"Venus {vdig} H{venus.get('house')}",
            chapter="D16 (Venus)",
        ))
    return out


def inspect_d20(d20: dict, pc: dict, _nav=None) -> list[RuleFinding]:
    """Spiritual-progress special checks — Jupiter/Ketu, 9th, 12th moksha house."""
    out: list[RuleFinding] = []
    planets = d20.get("planets", {})
    houses = d20.get("houses", {})
    jup, ketu = planets.get("Jupiter", {}), planets.get("Ketu", {})

    if jup and ketu and jup.get("sign") == ketu.get("sign"):
        out.append(RuleFinding(
            topic="Jupiter–Ketu together — the seeker's mark",
            verdict="favourable",
            detail=(
                "Jupiter (wisdom) and Ketu (liberation) share a sign in your devotion chart "
                "— a classical signature of genuine spiritual insight and a pull toward "
                "deeper practice as life goes on."
            ),
            highlight=True,
            why=f"Jupiter & Ketu both in {jup.get('sign','')}",
            chapter="D20 (Jupiter-Ketu)",
        ))

    ninth = houses.get(9, {})
    n_tenants = ninth.get("tenants", [])
    if any(t in _BENEFICS for t in n_tenants) or _dig_local(planets, "Jupiter") in _STRONG_DIG:
        out.append(RuleFinding(
            topic="The house of devotion (9th)",
            verdict="favourable",
            detail=(
                "The devotion house is well tenanted — faith comes naturally and matures "
                "into a steady, sustaining practice."
            ),
            highlight=True,
            why=f"D20 9th tenants {n_tenants or 'empty'}; Jupiter {_dig_local(planets,'Jupiter')}",
            chapter="D20 (9th / devotion)",
        ))

    twelfth = houses.get(12, {})
    t_tenants = twelfth.get("tenants", [])
    if any(t in _BENEFICS for t in t_tenants) or ketu.get("house") == 12:
        out.append(RuleFinding(
            topic="The liberation house (12th)",
            verdict="favourable",
            detail=(
                "The 12th — the house of meditation and surrender — is active, favouring "
                "retreat, inner silence, and a contemplative side that deepens with time."
            ),
            why=f"D20 12th tenants {t_tenants or 'empty'}",
            chapter="D20 (12th / moksha)",
        ))
    return out


def inspect_d40(d40: dict, pc: dict, _nav=None) -> list[RuleFinding]:
    """Maternal-legacy special checks — Moon and the 4th house."""
    out: list[RuleFinding] = []
    planets = d40.get("planets", {})
    houses = d40.get("houses", {})
    moon = planets.get("Moon", {})
    mdig = _dig_local(planets, "Moon")
    fourth = houses.get(4, {})
    tenants = fourth.get("tenants", [])

    if mdig in _STRONG_DIG or any(t in _BENEFICS for t in tenants):
        out.append(RuleFinding(
            topic="Maternal blessings (Moon & 4th)",
            verdict="favourable",
            detail=(
                "The Moon and the maternal house are well placed — strong, auspicious "
                "blessings carried down the mother's line, and a nourishing emotional "
                "inheritance."
            ),
            highlight=True,
            why=f"Moon {mdig} H{moon.get('house')}; D40 4th {tenants or 'empty'}",
            chapter="D40 (maternal line)",
        ))
    elif mdig in _WEAK_DIG or moon.get("house") in (6, 8, 12) or any(t in _MALEFICS for t in tenants):
        out.append(RuleFinding(
            topic="Maternal line (Moon & 4th)",
            verdict="caution",
            detail=(
                "The maternal axis is somewhat stressed — there may be inherited "
                "sensitivities or strain from the mother's side. Honouring that lineage "
                "and caring for the mother eases it."
            ),
            highlight=True,
            why=f"Moon {mdig} H{moon.get('house')}; D40 4th {tenants or 'empty'}",
            chapter="D40 (maternal line)",
        ))
    return out


def inspect_d45(d45: dict, pc: dict, _nav=None) -> list[RuleFinding]:
    """Paternal-legacy & character special checks — Sun and the 9th house."""
    out: list[RuleFinding] = []
    planets = d45.get("planets", {})
    houses = d45.get("houses", {})
    sun = planets.get("Sun", {})
    sdig = _dig_local(planets, "Sun")
    ninth = houses.get(9, {})
    tenants = ninth.get("tenants", [])

    if sdig in _STRONG_DIG or any(t in _BENEFICS for t in tenants):
        out.append(RuleFinding(
            topic="Paternal blessings & character (Sun & 9th)",
            verdict="favourable",
            detail=(
                "The Sun and the dharma house stand well — a strong moral grain, natural "
                "dignity, and good blessings carried from the father's side."
            ),
            highlight=True,
            why=f"Sun {sdig} H{sun.get('house')}; D45 9th {tenants or 'empty'}",
            chapter="D45 (paternal line / character)",
        ))
    elif sdig in _WEAK_DIG or sun.get("house") in (6, 8, 12) or any(t in _MALEFICS for t in tenants):
        out.append(RuleFinding(
            topic="Character tests & the paternal line (Sun & 9th)",
            verdict="caution",
            detail=(
                "The Sun/9th axis is under some pressure — life may test your principles, "
                "or there may be distance or strain with the father. Holding to integrity "
                "is the remedy the classics point to."
            ),
            highlight=True,
            why=f"Sun {sdig} H{sun.get('house')}; D45 9th {tenants or 'empty'}",
            chapter="D45 (paternal line / character)",
        ))
    return out


# Map of vargas that have a bespoke classical special-check inspector.
SPECIAL_INSPECTORS = {
    "D10": inspect_d10,
    "D12": inspect_d12,
    "D16": inspect_d16,
    "D20": inspect_d20,
    "D24": inspect_d24,
    "D27": inspect_d27,
    "D30": inspect_d30,
    "D40": inspect_d40,
    "D45": inspect_d45,
    "D60": inspect_d60,
}


# ----------------------------------------------------------------------------
# Presiding deity + chart-specific remedy per divisional chart
# ----------------------------------------------------------------------------
_PLANET_DEITY = {
    "Sun": ("Lord Shiva (Surya Bhagavan)", "offer arghya (water) to the rising Sun and recite the Aditya Hridayam or Gayatri"),
    "Moon": ("Goddess Parvati / Gauri (Chandra)", "worship the Divine Mother on Mondays and offer something white; keep a calm mind"),
    "Mars": ("Lord Hanuman (also Kartikeya)", "read the Hanuman Chalisa on Tuesdays and serve with disciplined energy"),
    "Mercury": ("Lord Vishnu (Budha)", "recite Vishnu Sahasranama, help students, and keep your word"),
    "Jupiter": ("Lord Vishnu / Dakshinamurthy (Brihaspati)", "honour your guru and elders, study scripture, and give to genuine causes on Thursdays"),
    "Venus": ("Goddess Lakshmi (Shukra)", "worship Lakshmi on Fridays, cultivate beauty and devotion, and respect your partner"),
    "Saturn": ("Lord Shani / Lord Hanuman", "serve workers and the needy, light a sesame-oil lamp on Saturdays, and stay patient and consistent"),
    "Rahu": ("Goddess Durga (Bhairava)", "worship Durga, recite the Durga Saptashati, and avoid shortcuts and deception"),
    "Ketu": ("Lord Ganesha (Bhairava)", "worship Ganesha before any new start, keep a simple spiritual practice, and donate multicoloured items"),
}
_PLANET_REMEDY_FULL = {
    "Sun": "Strengthen confidence and honour father-figures; the Sun's mantra on Sundays steadies authority and health.",
    "Moon": "Keep a calm routine and good sleep; honour your mother and offer something white on Mondays to steady the mind.",
    "Mars": "Channel energy through exercise and discipline; serve siblings and avoid rash anger on Tuesdays.",
    "Mercury": "Read, write and learn daily; keep your word and help students / donate green items on Wednesdays.",
    "Jupiter": "Seek a teacher's guidance and give to genuine causes; honour elders and study scripture on Thursdays.",
    "Venus": "Cultivate kindness and beauty in your home; respect your partner and offer something fragrant on Fridays.",
    "Saturn": "Be patient, consistent and of service to workers and elders; keep commitments and help the needy on Saturdays.",
    "Rahu": "Stay honest and grounded; worship Durga and avoid obsessive shortcuts — donate on eclipses and Saturdays.",
    "Ketu": "Keep a steady spiritual practice; worship Ganesha, and donate multicoloured or sesame items.",
}


def _focus_planet(chart: dict, karaka: str) -> tuple[str, str]:
    """Pick the planet whose deity/remedy most helps this chart's theme."""
    planets = chart.get("planets", {})
    ll = chart.get("lagna_lord", "")

    def weak(p: str) -> bool:
        b = planets.get(p, {})
        if not b:
            return False
        d = get_dignity(p, b.get("sign", "")) if b.get("sign") else "unknown"
        return d in _WEAK_DIG or b.get("house") in (6, 8, 12)

    if karaka and weak(karaka):
        return karaka, "carries this chart's main theme and is currently under some pressure"
    if ll and weak(ll):
        return ll, "rules this divisional chart and would benefit from strengthening"
    if karaka:
        return karaka, "is the natural significator of this chart's theme — honouring it sustains the good"
    return ll, "rules this divisional chart"


def varga_remedy_deity_html(chart: dict, varga: str, karaka: str, theme: str) -> str:
    """A chart-specific 'presiding deity + remedy' card for a divisional chart."""
    focus, reason = _focus_planet(chart, karaka)
    if not focus:
        return ""
    deity, worship = _PLANET_DEITY.get(focus, ("your ishta-devata", "keep a sincere daily practice"))
    remedy = _PLANET_REMEDY_FULL.get(focus, "")
    b = chart.get("planets", {}).get(focus, {})
    place = ""
    if b.get("house"):
        place = (f" In your {varga} chart it sits in the {_ord(b['house'])} house"
                 f" ({_dig_word(get_dignity(focus, b.get('sign','')) if b.get('sign') else 'unknown')}).")
    return (
        f'<h2 class="sec-hdr">Your deity &amp; remedy for this chart</h2>'
        f'<div class="deity-card">'
        f'<p><strong>Presiding planet:</strong> {_esc(focus)} — it {_esc(reason)}.{_esc(place)}</p>'
        f'<p><strong>Deity to honour:</strong> {_esc(deity)} — {_esc(worship)}.</p>'
        f'<p><strong>Remedy:</strong> {_esc(remedy)}</p>'
        f'<p class="rule-why">Remedies work as steady habits over months, not as instant fixes — '
        f'they gently strengthen {_esc(theme)}.</p>'
        f'</div>'
    )


# ----------------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------------
def _ord(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def _join(items: list[str]) -> str:
    items = [str(i) for i in items]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def _v(items: list, singular: str, plural: str) -> str:
    """Pick verb form that agrees with the count of items."""
    return singular if len(items) == 1 else plural


def _esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def rule_findings_html(
    findings: list[RuleFinding],
    title: str = "Every book rule, checked against your chart",
    intro: str = "",
) -> str:
    """Render findings prediction-first. Author-emphasised matches glow in colour."""
    if not findings:
        return ""
    hl_count = sum(1 for f in findings if f.highlight)
    intro = intro or (
        "The book states each rule, then proves it on a named example chart. "
        "Below, every rule is run against <em>your</em> chart. "
        + (f"<strong>{hl_count}</strong> place"
           f"{'s' if hl_count != 1 else ''} match a combination the author "
           f"specifically highlighted in a worked example — those are marked in colour."
           if hl_count else
           "None of the author's most-emphasised warning examples are active here.")
    )
    cards = []
    for f in findings:
        btxt, bcls = _VERDICT_BADGE.get(f.verdict, ("Noted", "neu"))
        cls = "rule-find"
        if f.highlight:
            cls += " flag"
        elif f.verdict == "caution":
            cls += " caution"
        elif f.verdict == "favourable":
            cls += " positive"
        else:
            cls += " neutral"
        star = ' <span class="bdg flag">author example</span>' if f.highlight else ""
        why = (f'<p class="rule-why">Why: {_esc(f.why)}'
               f'{" · " + _esc(f.chapter) if f.chapter else ""}</p>') if f.why or f.chapter else ""
        cards.append(
            f'<div class="{cls}">'
            f'<div class="rule-hdr"><strong>{_esc(f.topic)}</strong> '
            f'<span class="bdg {bcls}">{btxt}</span>{star}</div>'
            f'<p class="rule-detail">{f.detail}</p>{why}</div>'
        )
    return (
        f'<h2 class="sec-hdr">{_esc(title)}</h2>'
        f'<p class="rule-intro">{intro}</p>'
        f'<div class="rule-list">{"".join(cards)}</div>'
    )


def rule_inspection_css() -> str:
    return """
.rule-intro{font-size:.95rem;color:var(--muted);margin:6px 0 14px;line-height:1.55}
.rule-list{display:flex;flex-direction:column;gap:10px;margin-bottom:24px}
.rule-find{padding:13px 17px;border-radius:8px;border:1px solid var(--border);background:var(--card)}
.rule-find.positive{border-left:3px solid #1f6b42}
.rule-find.caution{border-left:3px solid #9a5a00}
.rule-find.neutral{border-left:3px solid #888}
.rule-find.flag{border-left:4px solid #7a4bd1;background:#f5f0fd;box-shadow:0 0 0 1px #e3d6f9 inset}
.rule-hdr{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-bottom:5px}
.rule-detail{margin:0;line-height:1.55;font-size:.95rem}
.rule-why{margin:6px 0 0;font-size:.78rem;color:var(--muted);font-style:italic}
.bdg.flag{background:#ece2fb;color:#5b2ec2}
mark.hl{background:#f0e6ff;color:#4a2a9a;padding:0 3px;border-radius:3px;font-weight:600}
.deity-card{margin:10px 0 24px;padding:15px 19px;border-radius:8px;border:1px solid var(--border);
  border-left:4px solid #b8860b;background:#fbf6ea}
.deity-card p{margin:.4rem 0;line-height:1.55}
"""
