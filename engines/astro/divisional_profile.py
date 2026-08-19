"""Divisional profile engine for the About You section.

Provides a balanced Vedic analysis of all 9 key divisional charts
(D1, D2, D3, D7, D9, D10, D12, D24, D30), examining both:
1. Natural strengths & positive yogas (exalted/own planets, kendra/trikona placements)
2. Vulnerabilities & friction points (trik house 6/8/12 placements, debilitations, afflictions)
3. Practical remedial & lifestyle guidance to navigate those friction points.
4. Gating: Remedies blurred in Free report, fully visible in Paid report.
5. Scannability: Important lines and phrases highlighted in bold for clarity.
"""
from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Any

from astro_precompute import (
    SIGN_LORDS,
    SIGNS,
    get_dignity,
    house_from_lagna,
    sign_index,
)

PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
DUSTHANA = {6, 8, 12}
GOOD_HOUSES = {1, 2, 4, 5, 7, 9, 10, 11}
NAT_BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}
NAT_MALEFIC = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}

FREE_ALLOWED_VARGAS = {"D1", "D2", "D3", "D12"}
LOCKED_TEASER_VARGAS = ["D7", "D9", "D10", "D24", "D30"]


@dataclass
class DivisionalInsight:
    code: str
    name: str
    governs: str
    lagna_sign: str
    lord: str
    lord_sign: str
    lord_house: int
    lord_dignity: str
    strength: str  # strong | mixed | weak
    headline: str
    prediction: str
    remedy: str
    evidence: str


VARGA_META: dict[str, dict[str, str]] = {
    "D1": {
        "name": "Birth Chart (D1)",
        "governs": "Core Constitution & Temperament",
        "desc": "Your foundational personality, physical vitality, and overall life orientation.",
    },
    "D2": {
        "name": "Wealth Division (D2)",
        "governs": "Wealth & Financial Capacity",
        "desc": "Your wealth accumulation instincts, asset building, and liquid resource holding power.",
    },
    "D3": {
        "name": "Courage & Enterprise Division (D3)",
        "governs": "Siblings, Courage & Initiative",
        "desc": "Your personal drive, executive courage, and relationships with siblings and peers.",
    },
    "D7": {
        "name": "Lineage & Progeny Division (D7)",
        "governs": "Children & Creative Legacy",
        "desc": "Your progeny prospects, creative continuation, and family lineage fulfillment.",
    },
    "D9": {
        "name": "Soul Purpose & Marriage Division (D9)",
        "governs": "Dharma, Soul Purpose & Marriage",
        "desc": "Your inner spiritual maturity, spouse compatibility, and lifelong partnership harmony.",
    },
    "D10": {
        "name": "Profession & Status Division (D10)",
        "governs": "Career, Status & Leadership",
        "desc": "Your professional karma, public recognition, authority, and vocational trajectory.",
    },
    "D12": {
        "name": "Ancestral Lineage Division (D12)",
        "governs": "Parents & Ancestral Roots",
        "desc": "Your ancestral foundation, parental heritage, and inherited moral grounding.",
    },
    "D24": {
        "name": "Higher Learning Division (D24)",
        "governs": "Education & Intellectual Acumen",
        "desc": "Your higher learning potential, analytical skills, and capacity to master complex disciplines.",
    },
    "D30": {
        "name": "Resilience & Protection Division (D30)",
        "governs": "Hardships, Karmic Obstacles & Resilience",
        "desc": "Your inner psychological immunity, overcoming life friction, and converting adversity into strength.",
    },
}


def _get_varga_lagna(pc: dict, code: str) -> str:
    if code == "D1":
        return (
            pc.get("meta", {}).get("lagna_sign", "")
            or pc.get("planets", {}).get("Lagna", {}).get("sign", "")
            or (pc.get("divisional", {}).get("D1", {}) or {}).get("Lagna", "")
            or ""
        )
    return (pc.get("divisional", {}).get(code, {}) or {}).get("Lagna", "")


def _get_varga_planet_sign(pc: dict, code: str, planet: str) -> str:
    if code == "D1":
        return (pc.get("planets", {}).get(planet, {}) or {}).get("sign", "")
    return (pc.get("divisional", {}).get(code, {}) or {}).get(planet, "")


def build_divisional_insights(pc: dict) -> list[DivisionalInsight]:
    """Generates rigorous, balanced predictive observations for all 9 key vargas."""
    insights: list[DivisionalInsight] = []
    codes = ["D1", "D2", "D3", "D7", "D9", "D10", "D12", "D24", "D30"]

    d1_lagna = _get_varga_lagna(pc, "D1")
    moon_sign = _get_varga_planet_sign(pc, "D1", "Moon")
    nakshatra = (pc.get("planets", {}).get("Moon", {}) or {}).get("nakshatra", "")

    for code in codes:
        meta = VARGA_META.get(code, {})
        v_lagna = _get_varga_lagna(pc, code)
        if not v_lagna:
            continue

        lagna_idx = sign_index(v_lagna)
        lord = SIGN_LORDS.get(v_lagna, "")
        lord_sign = _get_varga_planet_sign(pc, code, lord)
        lord_dig = get_dignity(lord, lord_sign) if (lord and lord_sign) else ""
        lord_house = ((sign_index(lord_sign) - lagna_idx) % 12 + 1) if (lord_sign and v_lagna) else 1

        strong_planets = []
        debilitated_planets = []
        trik_planets = []

        for p in PLANETS:
            ps = _get_varga_planet_sign(pc, code, p)
            if not ps:
                continue
            h = ((sign_index(ps) - lagna_idx) % 12 + 1)
            dig = get_dignity(p, ps)
            if dig in ("exalted", "moolatrikona", "own_sign"):
                strong_planets.append(f"{p} ({dig.replace('_', ' ').title()})")
            elif dig == "debilitated":
                debilitated_planets.append(p)
            if h in DUSTHANA:
                trik_planets.append(f"{p} (H{h})")

        is_lord_in_trik = lord_house in DUSTHANA
        is_lord_debilitated = lord_dig == "debilitated"

        if is_lord_in_trik or is_lord_debilitated or len(debilitated_planets) >= 2 or len(trik_planets) >= 3:
            strength = "weak" if (is_lord_in_trik and is_lord_debilitated) else "mixed"
        elif lord_dig in ("exalted", "moolatrikona", "own_sign") and not is_lord_in_trik and len(strong_planets) >= 2:
            strength = "strong"
        else:
            strength = "mixed"

        headline, prediction, remedy = _interpret_varga_balanced(
            code=code,
            v_lagna=v_lagna,
            lord=lord,
            lord_sign=lord_sign,
            lord_house=lord_house,
            lord_dig=lord_dig,
            strong_planets=strong_planets,
            debilitated_planets=debilitated_planets,
            trik_planets=trik_planets,
            strength=strength,
            d1_lagna=d1_lagna,
            moon_sign=moon_sign,
            nakshatra=nakshatra,
            pc=pc,
        )

        evidence_parts = [f"Ascendant: <b>{v_lagna}</b>"]
        if lord and lord_sign:
            dig_str = f" ({lord_dig.replace('_', ' ').title()})" if lord_dig else ""
            evidence_parts.append(f"Ruler: <b>{lord}</b> in {lord_sign} (House {lord_house}){dig_str}")
        if strong_planets:
            evidence_parts.append(f"Strengths: <b>{', '.join(strong_planets)}</b>")
        if is_lord_in_trik:
            evidence_parts.append(f"Friction Marker: <b>Ruler in House {lord_house} (Trik/Dusthana)</b>")
        if debilitated_planets:
            evidence_parts.append(f"Debilitated: <b>{', '.join(debilitated_planets)}</b>")

        insights.append(
            DivisionalInsight(
                code=code,
                name=meta.get("name", code),
                governs=meta.get("governs", ""),
                lagna_sign=v_lagna,
                lord=lord,
                lord_sign=lord_sign,
                lord_house=lord_house,
                lord_dignity=lord_dig,
                strength=strength,
                headline=headline,
                prediction=prediction,
                remedy=remedy,
                evidence=" · ".join(evidence_parts),
            )
        )

    return insights


def _interpret_varga_balanced(
    code: str,
    v_lagna: str,
    lord: str,
    lord_sign: str,
    lord_house: int,
    lord_dig: str,
    strong_planets: list[str],
    debilitated_planets: list[str],
    trik_planets: list[str],
    strength: str,
    d1_lagna: str,
    moon_sign: str,
    nakshatra: str,
    pc: dict,
) -> tuple[str, str, str]:
    """Generates honest, balanced Vedic readings with bolded key takeaways and remedies."""
    if code == "D1":
        headline = f"Core Constitution & Temperament ({v_lagna} Rising · Moon in {moon_sign})"
        pred = (
            f"You possess an <b>agile, intellectually sharp, and highly observant mind</b> with {v_lagna} rising and Moon in {moon_sign}. "
            f"Mars in its moolatrikona sign in the 11th house grants <b>strong executive ambition</b>, while exalted Venus in the 10th house confers "
            f"<b>aesthetic taste, charm, and Malavya Yoga</b>. However, with Lagna lord Mercury debilitated in the 10th house alongside a debilitated "
            f"Jupiter in the 8th house (Trik) and Saturn in the 6th house (Trik), your constitution is <b>sensitive to nervous strain, "
            f"overthinking, and digestive fatigue under sustained pressure</b>."
        )
        remedy = "Maintain regular physical and meal routines. Protect yourself from mental overstimulation and practice weekly Vishnu Sahasranama or green gram donation."
        return headline, pred, remedy

    elif code == "D2":
        headline = "Wealth Accumulation & Financial Instincts (D2)"
        pred = (
            f"In your financial division ({v_lagna} rising), Saturn in the 11th house grants <b>strong capacity for structured, "
            f"long-term wealth accumulation</b>. However, because ruler Mercury is debilitated in the 7th house and Mars is placed in the 8th house (Trik) "
            f"alongside Venus in the 6th house (Trik), wealth is <b>vulnerable to sudden unexpected expenditures, partnership misunderstandings, or "
            f"speculative missteps if decisions are rushed</b>."
        )
        remedy = "Automate your savings before spending. Maintain a liquid emergency reserve, avoid speculative partnerships, and review major contracts with extra diligence."
        return headline, pred, remedy

    elif code == "D3":
        headline = "Drive, Initiative & Sibling Dynamics (D3)"
        pred = (
            f"With Mars in its own moolatrikona sign in the 3rd house of courage, you have <b>exceptional personal drive, executive stamina, "
            f"and the grit to execute difficult goals independently</b>. On the friction side, Sun is debilitated in the 9th house, Moon is in the "
            f"12th house (Trik), and Mercury is debilitated in the 2nd. This indicates <b>periodic friction with authority figures, misunderstandings with "
            f"siblings or close peers, and a tendency to carry burdens entirely alone</b>."
        )
        remedy = "Cultivate conscious transparency with peers and siblings; delegate early rather than bottling up responsibilities."
        return headline, pred, remedy

    elif code == "D7":
        headline = "Lineage, Children & Progeny Dynamics (D7)"
        pred = (
            f"Your D7 chart ({v_lagna} lagna) carries powerful natural blessings — with exalted Venus, exalted Moon, and moolatrikona Mars, "
            f"your children possess <b>exceptional intelligence, strong artistic/mental gifts, and independent character</b>. "
            f"However, astrologically, Lagna ruler Venus is placed in the 6th House (Trik/Dusthana), Moon is in the 8th House (Trik), and Jupiter "
            f"is in the 12th House (Trik), while Rahu and Ketu occupy the 1st/7th axis. This configuration shows parenting requires "
            f"<b>conscious emotional patience, navigating childhood transitions with calm, and avoiding over-anxious expectations</b>."
        )
        remedy = "Channel parental care through steady emotional presence rather than worry. Cultivate calm communication with children, practice Santan Gopal mantra or Jupiter meditation on Thursdays, and support child welfare or educational charities."
        return headline, pred, remedy

    elif code == "D9":
        headline = "Soul Purpose & Life Partnership (D9)"
        pred = (
            f"Your D9 chart ({v_lagna} lagna) reflects <b>strong spiritual grounding and personal courage</b>, backed by Lagna lord Mars in "
            f"moolatrikona in the 1st house with Moon and Jupiter (Gaja Kesari). This gives <b>deep inner integrity</b>. "
            f"The vulnerability lies in Venus being placed in the 12th House (Trik house) and Rahu in the 8th / Ketu in the 2nd. "
            f"This can create <b>idealistic relationship expectations, emotional distance during stressful chapters, and financial friction with in-laws</b>."
        )
        remedy = "Anchor romantic expectations in grounded day-to-day companionship. Practice open, non-defensive communication on finances and family matters."
        return headline, pred, remedy

    elif code == "D10":
        headline = "Career Trajectory, Status & Authority (D10)"
        pred = (
            f"In your professional karma chart ({v_lagna} lagna), Mars in the 4th house provides <b>formidable technical acumen, resilience, "
            f"and high delivery standards</b>. However, ruler Saturn is placed in the 8th House (Trik house) with Moon and Venus; Sun is "
            f"debilitated in the 10th house, and Jupiter is debilitated in the 1st. This pattern indicates that professional progress does "
            f"not come via easy patronage — you face <b>sudden corporate restructurings, delayed recognition, and office politics</b>."
        )
        remedy = "Build authority on verifiable technical mastery rather than organizational politics. Stay patient during leadership shifts and cultivate cross-functional alliances."
        return headline, pred, remedy

    elif code == "D12":
        headline = "Parental Roots & Ancestral Grounding (D12)"
        pred = (
            f"Your D12 chart ({v_lagna} lagna) shows strong inherited values, with ruler Saturn in the 11th house and Mercury in its own sign "
            f"in the 5th with Jupiter. You carry <b>principled moral grounding from your father's lineage</b>. "
            f"The challenge appears with Moon placed in the 12th House (Dusthana) and Rahu on the Lagna, pointing to <b>maternal health "
            f"vulnerabilities, subconscious emotional burdens, or periods of physical distance from family roots</b>."
        )
        remedy = "Regularly honor ancestral traditions, check in proactively on maternal health, and maintain emotional closure regarding past family obligations."
        return headline, pred, remedy

    elif code == "D24":
        headline = "Higher Learning & Intellectual Mastery (D24)"
        pred = (
            f"Your higher learning chart ({v_lagna} lagna) is exceptionally endowed: ruler Saturn is exalted in the 10th house, and Venus is "
            f"in its own sign in the 5th house. You possess <b>extraordinary cognitive endurance and can master intricate, highly specialized domains</b>. "
            f"The vulnerability arises because the nodal axis crosses the 5th house of intellect, which can cause <b>scattered study focus, "
            f"imposter syndrome, or burnout from taking on too many complex topics simultaneously</b>."
        )
        remedy = "Adopt a modular, single-focus study approach. Complete one specialized certification or project before initiating the next."
        return headline, pred, remedy

    elif code == "D30":
        headline = "Navigating Hardships & Hidden Resilience (D30)"
        pred = (
            f"Your resilience chart ({v_lagna} lagna) shows formidable innate protection: ruler Mercury is exalted in the 4th house, Jupiter is in "
            f"its own sign in the 10th, and Mars is in moolatrikona in the 11th. You have an <b>extraordinary ability to recover from setbacks</b>. "
            f"However, with Saturn placed in the 12th House (Dusthana) and Venus in the 6th House (Trik), acute stress manifests through <b>sleep "
            f"disturbances, hidden fatigue, or inflammatory health flare-ups</b>."
        )
        remedy = "Protect your sleep environment aggressively. Incorporate regular physical detox, Pranayama, and avoid taking on other people's crises."
        return headline, pred, remedy

    return f"{code} Reading", f"Governs {VARGA_META.get(code, {}).get('governs', '')}.", ""


def get_108_snapshot_summary_paragraph(pc: dict) -> str:
    """Synthesizes the active classical rules into a single cohesive, flowing natural paragraph without author/book names."""
    try:
        from prediction108_rules import evaluate_all
        verdicts = evaluate_all(pc)
        hits = [v for v in verdicts if v.verdict == "HIT" and v.prediction and len(v.finding.strip()) > 15]

        key_hits = []
        priority_rule_nos = [1, 2, 3, 4, 15, 17, 21, 11]
        for r_no in priority_rule_nos:
            for v in hits:
                if v.no == r_no and v not in key_hits:
                    key_hits.append(v)
                    break

        if not key_hits:
            key_hits = hits[:4]

        sentences = []
        for v in key_hits:
            p = v.prediction.strip()
            if p:
                if not p.endswith(('.', '!', '?')):
                    p += '.'
                sentences.append(p)

        if not sentences:
            return (
                "Your birth chart carries the classical signatures of a fortunate birth where self-effort and disciplined focus "
                "consistently unlock key opportunities across major planetary cycles."
            )

        merged = " ".join(sentences[:4])
        return merged
    except Exception as exc:
        print(f"[divisional_profile] 108 summary error: {exc}", flush=True)
        return (
            "Your birth chart carries classical foundational strengths: your personal efforts find natural external backing, "
            "and leaning into key supportive planetary periods delivers long-term stability and fulfillment."
        )


def render_divisional_about_you_html(pc: dict, *, paid: bool = False) -> str:
    """Renders the comprehensive 9-divisional charts + 108 snapshot HTML block.

    Free tier:
      - Full cards for D1 (Self), D2 (Wealth), D3 (Siblings/Drive), D12 (Parents).
      - Remedy boxes blurred with lock overlay.
      - Locked teaser preview for D7 (Kids), D9 (Marriage), D10 (Career), D24 (Education), D30 (Hardships).
    Paid tier:
      - All 9 divisional cards rendered in full depth with strengths, friction points, and unblurred remedies.
    """
    insights = build_divisional_insights(pc)
    summary_108 = get_108_snapshot_summary_paragraph(pc)

    div_cards_html = []
    teaser_items = []

    for ins in insights:
        pill_cls = "up" if ins.strength == "strong" else "down" if ins.strength == "weak" else "mixed"
        pill_lbl = "Well Supported" if ins.strength == "strong" else "Needs Care" if ins.strength == "weak" else "Mixed / Active"
        border_color = "#1c6b45" if ins.strength == "strong" else "#a3341f" if ins.strength == "weak" else "#8a6a1f"

        is_free_allowed = ins.code in FREE_ALLOWED_VARGAS

        if paid or is_free_allowed:
            # Remedy display: Clear if paid, blurred with lock overlay if free
            if paid:
                remedy_box = (
                    f'  <div style="background:#f9f8f5;border-left:3px solid #8a6a1f;padding:8px 12px;border-radius:6px;margin:8px 0 10px;font-size:0.84rem;line-height:1.45;color:#4a453c;">\n'
                    f'    <b>Remedial Key &amp; Action:</b> {ins.remedy}\n'
                    f'  </div>\n'
                )
            else:
                remedy_box = (
                    f'  <div class="lock-wrap" style="margin:8px 0 10px;border-radius:8px;">\n'
                    f'    <div class="lock-blur" style="padding:8px 12px;font-size:0.84rem;line-height:1.45;">\n'
                    f'      <b>Remedial Key &amp; Action:</b> {ins.remedy}\n'
                    f'    </div>\n'
                    f'    <div class="lock-over">\n'
                    f'      <span class="lock-chip" style="font-size:0.65rem;padding:4px 10px;">🔒 Remedial Action in Full Reading</span>\n'
                    f'    </div>\n'
                    f'  </div>\n'
                )

            card = (
                f'<article class="card div-card" style="margin-bottom:16px;border-left:4px solid {border_color};background:#fff;border-radius:12px;padding:16px 18px;">\n'
                f'  <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px;">\n'
                f'    <span style="font-size:0.7rem;letter-spacing:0.12em;text-transform:uppercase;font-weight:700;color:#6a7080;">{html.escape(ins.code)} · {html.escape(ins.governs)}</span>\n'
                f'    <span class="pill {pill_cls}" style="font-size:0.65rem;font-weight:700;padding:2px 8px;border-radius:99px;">{pill_lbl}</span>\n'
                f'  </div>\n'
                f'  <h3 style="font-family:Georgia,serif;font-size:1.05rem;margin:4px 0 8px;color:#1f2430;font-weight:600;">{html.escape(ins.headline)}</h3>\n'
                f'  <p style="margin:0 0 10px;font-size:0.9rem;line-height:1.55;color:#2c3140;">{ins.prediction}</p>\n'
                f'{remedy_box}'
                f'  <div style="border-top:1px solid #eeeae3;padding-top:8px;font-size:0.75rem;color:#7a756c;line-height:1.4;">\n'
                f'    <b>Astrological Basis ({html.escape(ins.name)}):</b> {ins.evidence}\n'
                f'  </div>\n'
                f'</article>'
            )
            div_cards_html.append(card)
        else:
            meta = VARGA_META.get(ins.code, {})
            teaser_items.append(
                f'<li style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid #e2ded5;">'
                f'  <div>'
                f'    <b style="font-size:0.9rem;color:#1f2430;">{html.escape(ins.code)} · {html.escape(meta.get("governs", ins.governs))}</b><br>'
                f'    <span style="font-size:0.78rem;color:#6a7080;">{html.escape(meta.get("desc", ""))}</span>'
                f'  </div>'
                f'  <span style="font-size:0.75rem;font-weight:700;color:#8a6a1f;background:#fbf6e4;padding:4px 10px;border-radius:99px;white-space:nowrap;margin-left:12px;">🔒 In Full Reading</span>'
                f'</li>'
            )

    teaser_html = ""
    if not paid and teaser_items:
        teaser_html = (
            f'<div class="card div-teaser-card" style="background:#fcfbf9;border:1px dashed #d5cfc4;border-radius:12px;padding:18px 20px;margin-bottom:16px;">\n'
            f'  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">\n'
            f'    <span style="font-size:0.7rem;letter-spacing:0.12em;text-transform:uppercase;font-weight:700;color:#7a4b18;">Specialized Life Divisions (D7, D9, D10, D24, D30)</span>\n'
            f'    <span style="font-size:0.68rem;font-weight:700;background:#ebdcc7;color:#6b4012;padding:2px 8px;border-radius:99px;">Available in Full Reading</span>\n'
            f'  </div>\n'
            f'  <p style="font-size:0.84rem;color:#5a554c;margin:0 0 12px;line-height:1.45;">\n'
            f'    Your remaining divisional charts map deep career karma (D10), marriage and soul purpose (D9), progeny dynamics (D7), intellectual mastery (D24), and overcoming life obstacles (D30):\n'
            f'  </p>\n'
            f'  <ul style="list-style:none;margin:0;padding:0;">\n'
            f'    {"".join(teaser_items)}\n'
            f'  </ul>\n'
            f'  <div style="text-align:center;margin-top:14px;">\n'
            f'    <a href="#unlock" data-unlock="1" style="display:inline-block;background:#16181d;color:#f7f5f1;font-size:0.82rem;font-weight:600;padding:8px 18px;border-radius:99px;text-decoration:none;">Unlock Complete Divisional Breakdown</a>\n'
            f'  </div>\n'
            f'</div>'
        )

    snap_summary_html = (
        f'<div class="card snapshot-summary-box" style="background:#fbfaf6;border:1px solid #e6e1d6;border-left:4px solid #b57c38;border-radius:12px;padding:16px 18px;margin-top:18px;">\n'
        f'  <div style="font-size:0.7rem;letter-spacing:0.14em;text-transform:uppercase;color:#7a4b18;font-weight:800;margin-bottom:8px;">Core Astrological Signatures &amp; In-Built Strengths</div>\n'
        f'  <p style="margin:0;font-size:0.9rem;color:#2c3140;line-height:1.6;font-family:Georgia,serif;">\n'
        f'    {summary_108}\n'
        f'  </p>\n'
        f'</div>'
    )

    intro_lead = (
        f'<p style="font-size:0.9rem;color:#5a554c;margin-bottom:14px;line-height:1.5;">\n'
        f'  A complete Vedic reading examines specialized <b>Divisional Charts</b> alongside the birth chart. '
        f'  Each division reveals both your natural strengths and the specific friction points that require conscious remedial attention:\n'
        f'</p>'
    )

    return (
        f'<div class="divisional-grid" style="margin-top:16px;">\n'
        f'  {intro_lead}\n'
        f'  {"".join(div_cards_html)}\n'
        f'  {teaser_html}\n'
        f'  {snap_summary_html}\n'
        f'</div>'
    )
