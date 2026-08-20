"""Divisional profile engine for the About You & Life Foundations section.

Provides a warm, highly specific, and accessible Vedic analysis of all key divisional charts
(D1, D2, D3, D4, D7, D9, D10, D12, D24, D30), delivering:
1. Chart-Specific Life Insights:
   - D10: Tailored career fields, executive archetype, and optimal work style based on 10th lords, D10 Lagna/10th house & Amatyakaraka.
   - D9: Specific life partner characteristics, marital dynamics, and Bhagyodaya path based on 7th lords & D9 Lagna.
   - D2: Practical wealth generation streams and asset retention instincts.
   - D3: Everyday initiative & drive (or early speech/motor development roadmap for children).
   - D7: Progeny promise, parenting style, and family expansion timeline.
   - D24: Ideal academic disciplines, intellectual strengths, and skill mastery.
   - D30: Physical stress points, vitality preservation, and inner resilience.
2. Domain-Specific Timelines (Non-repeating, tailored impact of running dasha on that specific life area).
3. Actionable Vedic Upaya (Practical, compassionate remedies).
4. Collapsible Technical Astrological Proof (<details> drawer for houses, lords, degrees, and dignities).
5. Gating: Remedies and deeper divisional charts unlocked in Paid tier, previewed in Free tier.
"""
from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import date
from typing import Any, Optional

from astro_precompute import (
    SIGN_LORDS,
    SIGNS,
    get_dignity,
    house_from_lagna,
    sign_index,
)


def house_sign(lagna: str, h: int) -> str:
    if not lagna or lagna not in SIGNS:
        return ""
    idx = (SIGNS.index(lagna) + (h - 1)) % 12
    return SIGNS[idx]


PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
DUSTHANA = {6, 8, 12}
GOOD_HOUSES = {1, 2, 4, 5, 7, 9, 10, 11}
NAT_BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}
NAT_MALEFIC = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}

FREE_ALLOWED_VARGAS = {"D1", "D2", "D3", "D12"}
LOCKED_TEASER_VARGAS = ["D7", "D9", "D10", "D24", "D30"]

ORDINALS = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th", 6: "6th", 7: "7th", 8: "8th", 9: "9th", 10: "10th", 11: "11th", 12: "12th"}


@dataclass
class DivisionalInsight:
    code: str
    name: str
    governs: str
    domain_id: str
    lagna_sign: str
    lord: str
    lord_sign: str
    lord_house: int
    lord_dignity: str
    strength: str  # strong | mixed | weak
    headline: str
    prediction: str
    timeline: str
    remedy: str
    evidence: str


VARGA_META: dict[str, dict[str, str]] = {
    "D1": {
        "name": "Birth Chart (D1)",
        "governs": "Core Nature & Personal Vitality",
        "desc": "Your foundational personality, physical vitality, and overall life orientation.",
    },
    "D2": {
        "name": "Wealth Division (D2 · Hora)",
        "governs": "Wealth, Savings & Financial Stability",
        "desc": "Your wealth accumulation instincts, asset building, and liquid resource holding power.",
    },
    "D3": {
        "name": "Courage, Siblings & Initiative (D3 · Drekkana)",
        "governs": "Siblings, Courage & Initiative",
        "desc": "Your courage, everyday initiative, sibling relationships, and physical execution drive.",
    },
    "D4": {
        "name": "Property & Fixed Assets (D4 · Chaturthamsha)",
        "governs": "Home, Land, Vehicles & Domestic Peace",
        "desc": "Fixed property ownership, land assets, conveyances, and long-term domestic security.",
    },
    "D7": {
        "name": "Children & Lineage (D7 · Saptamsha)",
        "governs": "Children, Family Continuation & Legacy",
        "desc": "Your progeny prospects, reproductive vitality, family continuation, and children's dharma.",
    },
    "D9": {
        "name": "Marriage & Soul Journey (D9 · Navamsha)",
        "governs": "Life Partner, Marriage & Inner Growth",
        "desc": "Your inner spiritual maturity, spouse compatibility, and lifelong partnership harmony.",
    },
    "D10": {
        "name": "Career & Profession (D10 · Dasamsha)",
        "governs": "Career Growth, Status & Public Respect",
        "desc": "Your professional karma, public recognition, authority, and vocational trajectory.",
    },
    "D12": {
        "name": "Family Roots (D12 · Dwadashamsha)",
        "governs": "Parents & Ancestral Blessings",
        "desc": "Your ancestral foundation, parental heritage, and inherited moral grounding.",
    },
    "D24": {
        "name": "Higher Learning (D24 · Chaturvimshamsha)",
        "governs": "Education, Memory & Intellectual Skills",
        "desc": "Your higher learning potential, analytical skills, and capacity to master complex disciplines.",
    },
    "D30": {
        "name": "Health & Resilience (D30 · Trimsamsha)",
        "governs": "Overcoming Obstacles & Inner Immunity",
        "desc": "Your inner physiological/psychological resilience, latent sensitivities, and crisis recovery.",
    },
}

PLANET_REMEDIES: dict[str, dict[str, str]] = {
    "Sun": {
        "strengthen": "Offer fresh water to the morning sun daily (Surya Arghya) with a calm mind; nurture respect for elders and father figures.",
        "dusthana": "Recite the Aditya Hridaya Stotram on Sundays; donate copper, wheat, or jaggery to support those in need.",
        "debilitated": "Chant 'Om Hram Hreem Hroum Sah Suryaya Namah' at sunrise; practice daily acts of kindness without seeking validation.",
    },
    "Moon": {
        "strengthen": "Perform Monday Jal Abhishek with clean water on Shiva Lingam; practice mindful hydration, calm breathing, and love for mother.",
        "dusthana": "Chant the Chandra Gayatri Mantra on Monday evenings; keep living spaces clean, well-lit, and peaceful.",
        "debilitated": "Chant 'Om Shram Shreem Shroum Sah Chandraya Namah'; offer milk or food to cows on Mondays to soothe emotional stress.",
    },
    "Mars": {
        "strengthen": "Read the Hanuman Chalisa on Tuesdays; channel physical energy into regular outdoor sports, yoga, or martial discipline.",
        "dusthana": "Chant the Mangal Gayatri Mantra; practice deep breathing before speaking in heated moments; donate red lentils (masoor dal).",
        "debilitated": "Chant 'Om Kram Kreem Kroum Sah Bhaumaya Namah'; practice patience, gentleness, and supporting siblings.",
    },
    "Mercury": {
        "strengthen": "Offer fresh green grass or spinach to cows on Wednesdays; chant the Budha Gayatri Mantra or practice daily reading aloud.",
        "dusthana": "Chant 'Om Bram Breem Broum Sah Budhaya Namah' on Wednesdays; engage in structured speech practice, vocal recitation, and puzzles.",
        "debilitated": "Wear green shades on Wednesdays; practice attentive listening; donate educational books or notebooks to young students.",
    },
    "Jupiter": {
        "strengthen": "Honor teachers and mentors on Thursdays; chant the Brihaspati Gayatri Mantra; maintain truthfulness and moral kindness.",
        "dusthana": "Chant 'Om Gram Greem Groum Sah Gurave Namah' on Thursdays; donate yellow fruits (bananas) or turmeric at a spiritual place.",
        "debilitated": "Offer yellow food to elders on Thursdays; maintain steady humility, wisdom, and lifelong learning.",
    },
    "Venus": {
        "strengthen": "Chant the Shukra Gayatri Mantra; cultivate artistic appreciation, clean surroundings, and harmony in the home.",
        "dusthana": "Chant 'Om Dram Dreem Droum Sah Shukraya Namah' on Fridays; support women's welfare initiatives or donate sweets.",
        "debilitated": "Practice genuine devotion and self-respect; avoid impulsive emotional attachments; donate white grains on Fridays.",
    },
    "Saturn": {
        "strengthen": "Light a sesame oil lamp on Saturday evenings; cultivate patience, humility, and steady, disciplined effort.",
        "dusthana": "Recite the Dasharatha Shani Stotram on Saturdays; feed stray animals or support elderly and working-class people.",
        "debilitated": "Chant 'Om Pram Preem Proum Sah Shanaischaraya Namah'; stay physically active; avoid procrastination.",
    },
    "Rahu": {
        "strengthen": "Chant the Saraswati Vandana daily; avoid speculative rumors; maintain clean, uncluttered living spaces.",
        "dusthana": "Chant 'Om Bhram Bhreem Bhroum Sah Rahave Namah' during twilight; donate dark blankets or mustard seeds to those in need.",
        "debilitated": "Practice daily meditation to still an overactive imagination; limit excessive screen time and digital stimulation.",
    },
    "Ketu": {
        "strengthen": "Chant the Ganesha Atharvashirsha on Tuesdays; cultivate inner reflection, pranayama, and simple, peaceful living.",
        "dusthana": "Chant 'Om Stram Streem Stroum Sah Ketave Namah'; feed multi-colored dogs; donate warm clothes in winter.",
        "debilitated": "Practice deep diaphragmatic breathing (Pranayama) daily; offer grains to birds in the morning.",
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


def _format_month_year(date_str: str) -> str:
    if not date_str or len(date_str) < 7:
        return date_str
    try:
        y, m = int(date_str[:4]), int(date_str[5:7])
        month_names = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        if 1 <= m <= 12:
            return f"{month_names[m]} {y}"
    except Exception:
        pass
    return date_str[:7]


def _build_domain_specific_timeline(
    pc: dict,
    code: str,
    current_age: int,
    curr_md: str,
    curr_ad_name: str,
    curr_ad_end: str,
    adulthood_md: str,
    adulthood_start_yr: int,
) -> str:
    """Builds distinct, domain-specific multi-clock confluence timeline guidance (Vimshottari + Jaimini Chara + Yogini Antardashas + Transits)."""
    is_child = current_age < 18
    this_yr = date.today().year
    t_now = date.today()

    # 1. Vimshottari Data
    vim = pc.get("vimshottari", {})
    curr_ad_list = vim.get("current_md_antardashas", [])

    curr_ad = None
    future_ads = []
    for ad in curr_ad_list:
        st = ad.get("status") or ("current" if ad.get("is_current") else "")
        if st == "current" or ad.get("is_current"):
            curr_ad = ad
        elif st == "future":
            future_ads.append(ad)

    if not curr_ad and curr_ad_list:
        curr_ad = curr_ad_list[0]

    curr_ad_lord = curr_ad.get("ad_lord") or curr_ad.get("antardasha") or curr_ad_name or "Sub-period"
    curr_ad_end_fmt = _format_month_year(str(curr_ad.get("end") or "")) or curr_ad_end

    # 2. Jaimini Chara Dasha Data
    jaimini = pc.get("jaimini", {})
    chara = jaimini.get("chara_dasha", {})
    curr_chara_m = chara.get("current_maha", {}) if isinstance(chara, dict) else {}
    curr_chara_a = chara.get("current_antar", {}) if isinstance(chara, dict) else {}
    chara_m_sign = curr_chara_m.get("sign", "")
    chara_m_end = _format_month_year(str(curr_chara_m.get("end") or ""))
    chara_a_sign = curr_chara_a.get("sign", "")

    # 3. Yogini Dasha Data (Progressive Antardashas)
    dob_raw = pc.get("meta", {}).get("birth_date") or pc.get("meta", {}).get("dob") or pc.get("dob")
    dob_d = date.fromisoformat(str(dob_raw)[:10]) if dob_raw else date(this_yr - current_age, 1, 1)
    moon_nak = str((pc.get("planets", {}).get("Moon", {}) or {}).get("nakshatra", "Hasta"))
    moon_deg = float((pc.get("planets", {}).get("Moon", {}) or {}).get("degree_in_sign", 0.0) or 0.0) % 13.333333

    active_yog_antar = None
    future_yog_antars = []
    try:
        from chara_yogini_timing import build_progressive_yogini_periods
        all_y_antars = build_progressive_yogini_periods(dob_d, moon_nak, moon_deg)
        for p in all_y_antars:
            p_st = p.get("start")
            p_en = p.get("end")
            if isinstance(p_st, str): p_st = date.fromisoformat(p_st[:10])
            if isinstance(p_en, str): p_en = date.fromisoformat(p_en[:10])
            if p_st and p_en:
                if p_st <= t_now <= p_en:
                    active_yog_antar = p
                elif p_st > t_now:
                    future_yog_antars.append(p)
    except Exception:
        pass

    if active_yog_antar:
        yog_display = f"{active_yog_antar['maha_yogini']}-{active_yog_antar['yogini']} ({active_yog_antar['lord']})"
    else:
        yogini = pc.get("yogini", {})
        curr_yog = yogini.get("current_yogini", {}) if isinstance(yogini, dict) else {}
        yog_display = f"{curr_yog.get('yogini', 'Ulka')} ({curr_yog.get('lord', 'Saturn')})"

    def get_yogini_support(target_lords: list[str]) -> str:
        for yp in future_yog_antars[:6]:
            if yp.get("lord") in target_lords or yp.get("yogini") in target_lords:
                y_st = _format_month_year(str(yp.get("start") or ""))
                y_en = _format_month_year(str(yp.get("end") or ""))
                if y_st and y_en:
                    return f" (amplified by <b>Yogini {yp['maha_yogini']}-{yp['yogini']}</b> phase from {y_st} to {y_en})"
        return ""

    # 4. Karakas & Lords
    k_list = jaimini.get("karakas", [])
    k_map = {}
    if isinstance(k_list, list):
        for k_obj in k_list:
            r = str(k_obj.get("role", "")).upper()
            p = str(k_obj.get("planet", ""))
            if "ATMA" in r: k_map["AK"] = p
            elif "AMATYA" in r: k_map["AmK"] = p
            elif "BHRATRU" in r: k_map["BK"] = p
            elif "MATRU" in r: k_map["MK"] = p
            elif "PUTRA" in r: k_map["PK"] = p
            elif "GNATI" in r: k_map["GK"] = p
            elif "DARA" in r: k_map["DK"] = p
    elif isinstance(k_list, dict):
        k_map = k_list

    ak = k_map.get("AK", "Sun")
    amk = k_map.get("AmK", "Sun")
    bk = k_map.get("BK", "Mars")
    mk = k_map.get("MK", "Moon")
    pk = k_map.get("PK", "Jupiter")
    gk = k_map.get("GK", "Saturn")
    dk = k_map.get("DK", "Venus")

    d1_lagna = pc.get("meta", {}).get("lagna_sign", "") or (pc.get("lagna", {}) or {}).get("sign", "Gemini")

    def get_h_lord(h: int) -> str:
        if not d1_lagna or d1_lagna not in SIGNS:
            return ""
        s = SIGNS[(SIGNS.index(d1_lagna) + h - 1) % 12]
        return SIGN_LORDS.get(s, "")

    h10_lord = get_h_lord(10)
    h7_lord = get_h_lord(7)
    h2_lord = get_h_lord(2)
    h11_lord = get_h_lord(11)
    h5_lord = get_h_lord(5)
    h4_lord = get_h_lord(4)
    h3_lord = get_h_lord(3)
    h9_lord = get_h_lord(9)

    def find_future_ad(target_lords: list[str]) -> tuple[str, str, str]:
        for t in target_lords:
            for ad in future_ads:
                l = ad.get("ad_lord") or ad.get("antardasha") or ""
                if l == t:
                    st = _format_month_year(str(ad.get("start") or ""))
                    en = _format_month_year(str(ad.get("end") or ""))
                    return l, st, en
        if future_ads:
            ad = future_ads[0]
            l = ad.get("ad_lord") or ad.get("antardasha") or ""
            st = _format_month_year(str(ad.get("start") or ""))
            en = _format_month_year(str(ad.get("end") or ""))
            return l, st, en
        return "", "", ""

    # Multi-Clock Status Line
    chara_str = f" · Chara Dasha: <b>{chara_m_sign}{f'-{chara_a_sign}' if chara_a_sign else ''}</b>" if chara_m_sign else ""
    yog_str = f" · Yogini: <b>{yog_display}</b>" if yog_display else ""
    active_clocks = f"<b>Active Multi-Clock Alignment:</b> Vimshottari <b>{curr_md}-{curr_ad_lord}</b> (until {curr_ad_end_fmt}){chara_str}{yog_str}."

    if code == "D10":
        # Career
        if is_child:
            launch_yr = this_yr + (22 - current_age)
            peak_yr = this_yr + (28 - current_age)
            return (
                f"{active_clocks}<br>"
                f"<b>Vocational Incubation Phase:</b> Currently building academic curiosity and intellectual discipline under {curr_md}-{curr_ad_lord}.<br>"
                f"<b>Key Career Milestones:</b> <b>Career Launch Window:</b> <span style='color:#b57c38;font-weight:700;'>{launch_yr}–{launch_yr+4} (Ages 22–26)</span> | "
                f"<b>Executive Promotion & Authority Surge:</b> <span style='color:#b57c38;font-weight:700;'>{peak_yr}–{peak_yr+6} (Ages 28–34)</span>."
            )
        else:
            c_lord, c_st, c_en = find_future_ad([amk, h10_lord, "Sun", "Jupiter", "Venus", "Mars"])
            yog_boost = get_yogini_support(["Sun", "Mercury", "Jupiter", "Pingala", "Bhadrika", "Dhanya"])
            next_chara_info = f" Aligned with the upcoming <b>{chara_m_sign} → next major Chara cycle ({chara_m_end})</b>" if chara_m_end else ""
            return (
                f"{active_clocks}<br>"
                f"<b>Active Career Momentum:</b> Strategic consolidation and positioning under {curr_md}-{curr_ad_lord} (running until {curr_ad_end_fmt}).<br>"
                f"<b>Career Surge & Executive Elevation Window:</b> <span style='color:#b57c38;font-weight:700;'>{c_st} – {c_en}</span> under <b>{curr_md}-{c_lord}</b> "
                f"(activating Amatyakaraka {amk} and 10th house authority){yog_boost}.{next_chara_info}."
            )

    elif code == "D9":
        # Marriage
        if is_child:
            m_yr = this_yr + (26 - current_age)
            return (
                f"{active_clocks}<br>"
                f"<b>Partnership Horizon:</b> <b>Prime Marriage Window:</b> <span style='color:#b57c38;font-weight:700;'>{m_yr}–{m_yr+5} (Ages 26–31)</span> "
                f"under supportive Venus and 7th house planetary activations."
            )
        else:
            m_lord, m_st, m_en = find_future_ad([dk, "Venus", h7_lord, "Jupiter"])
            yog_boost = get_yogini_support(["Venus", "Jupiter", "Siddha", "Dhanya"])
            return (
                f"{active_clocks}<br>"
                f"<b>Relationship Dynamics:</b> Emotional grounding and mutual understanding under {curr_md}-{curr_ad_lord} (until {curr_ad_end_fmt}).<br>"
                f"<b>Marital Fruition & Relational Harmony Window:</b> <span style='color:#b57c38;font-weight:700;'>{m_st} – {m_en}</span> under <b>{curr_md}-{m_lord}</b> "
                f"(activating Darakaraka {dk} and 7th house partnership karaka){yog_boost}."
            )

    elif code == "D2":
        # Wealth
        w_lord, w_st, w_en = find_future_ad([h2_lord, h11_lord, "Jupiter", "Venus", "Mercury"])
        yog_boost = get_yogini_support(["Jupiter", "Venus", "Mercury", "Dhanya", "Siddha", "Bhadrika"])
        return (
            f"{active_clocks}<br>"
            f"<b>Financial Rhythm:</b> Structured capital preservation and disciplined compounding under {curr_md}-{curr_ad_lord} (until {curr_ad_end_fmt}).<br>"
            f"<b>Major Asset Accumulation & Liquidity Window:</b> <span style='color:#b57c38;font-weight:700;'>{w_st} – {w_en}</span> under <b>{curr_md}-{w_lord}</b> "
            f"favoring high-yield compounding, asset acquisitions, and expanding income streams{yog_boost}."
        )

    elif code == "D7":
        # Children
        if is_child:
            p_yr = this_yr + (28 - current_age)
            return (
                f"{active_clocks}<br>"
                f"<b>Family Continuation Horizon:</b> <b>Primary Progeny Window:</b> <span style='color:#b57c38;font-weight:700;'>{p_yr}–{p_yr+5} (Ages 28–33)</span> "
                f"when Putrakaraka and 5th house significators activate."
            )
        else:
            p_lord, p_st, p_en = find_future_ad([pk, h5_lord, "Jupiter", "Moon", "Venus"])
            yog_boost = get_yogini_support(["Jupiter", "Moon", "Venus", "Dhanya", "Mangala", "Siddha"])
            return (
                f"{active_clocks}<br>"
                f"<b>Family Continuation Dynamics:</b> Foundational family nurturing under {curr_md}-{curr_ad_lord} (until {curr_ad_end_fmt}).<br>"
                f"<b>Progeny Blessing & Family Expansion Window:</b> <span style='color:#b57c38;font-weight:700;'>{p_st} – {p_en}</span> under <b>{curr_md}-{p_lord}</b> "
                f"(activating Putrakaraka {pk} and 5th house fertility guardians){yog_boost}."
            )

    elif code == "D24":
        # Learning
        l_lord, l_st, l_en = find_future_ad(["Mercury", "Jupiter", h5_lord, h4_lord, "Sun"])
        yog_boost = get_yogini_support(["Mercury", "Jupiter", "Bhadrika", "Dhanya"])
        return (
            f"{active_clocks}<br>"
            f"<b>Intellectual Grasping Power:</b> Deep analytical assimilation and conceptual mastery under {curr_md}-{curr_ad_lord} (until {curr_ad_end_fmt}).<br>"
            f"<b>Academic Distinction & Certification Milestone:</b> <span style='color:#b57c38;font-weight:700;'>{l_st} – {l_en}</span> under <b>{curr_md}-{l_lord}</b>, "
            f"energizing executive credentials, specialized publications, and competitive examinations{yog_boost}."
        )

    elif code == "D4":
        # Home & Property
        prop_lord, prop_st, prop_en = find_future_ad(["Mars", "Venus", h4_lord, "Jupiter"])
        yog_boost = get_yogini_support(["Mars", "Venus", "Bhramari", "Siddha"])
        return (
            f"{active_clocks}<br>"
            f"<b>Domestic Sanctuary & Real Estate Timing:</b> Property consolidation under {curr_md}-{curr_ad_lord} (until {curr_ad_end_fmt}).<br>"
            f"<b>Prime Property Acquisition & Vehicle Upgrade Window:</b> <span style='color:#b57c38;font-weight:700;'>{prop_st} – {prop_en}</span> under <b>{curr_md}-{prop_lord}</b> "
            f"(activating Bhoomi Karaka Mars and 4th house fixed assets){yog_boost}."
        )

    elif code == "D30":
        # Health
        if is_child:
            rec_lord, rec_st, rec_en = find_future_ad(["Mercury", "Jupiter", "Venus", "Moon"])
            return (
                f"{active_clocks}<br>"
                f"<b>Vitality & Nervous Regulation:</b> Building foundational nervous and digestive strength.<br>"
                f"<b>Major Healing & Physical Fortification Window:</b> <span style='color:#b57c38;font-weight:700;'>{rec_st} – {rec_en}</span> under <b>{curr_md}-{rec_lord}</b>, "
                f"delivering rapid sensory recovery, emotional calm, and robust physical stamina."
            )
        else:
            rec_lord, rec_st, rec_en = find_future_ad(["Jupiter", "Venus", "Sun", "Mercury", "Moon"])
            return (
                f"{active_clocks}<br>"
                f"<b>Immunity & Stress Rhythm:</b> Regulating work-rest balance under {curr_md}-{curr_ad_lord} (until {curr_ad_end_fmt}) during active {yog_display} Yogini cycle.<br>"
                f"<b>Peak Vitality & Rejuvenation Window:</b> <span style='color:#b57c38;font-weight:700;'>{rec_st} – {rec_en}</span> under <b>{curr_md}-{rec_lord}</b>, "
                f"bringing deep physical rejuvenation, stress release, and cellular vitality."
            )

    elif code == "D3":
        # Siblings & Initiative
        if is_child:
            sp_lord, sp_st, sp_en = find_future_ad(["Mercury", "Jupiter", "Venus", "Moon"])
            return (
                f"{active_clocks}<br>"
                f"<b>Expressive Speech & Motor Pacing:</b> Active motor coordination under {curr_md}-{curr_ad_lord}.<br>"
                f"<b>Expressive Breakthrough Window:</b> <span style='color:#b57c38;font-weight:700;'>{sp_st} – {sp_en}</span> under <b>{curr_md}-{sp_lord}</b>, "
                f"activating vocal clarity, fluent sentence formation, and confident physical coordination."
            )
        else:
            dr_lord, dr_st, dr_en = find_future_ad([bk, "Mars", h3_lord, "Mercury", "Venus"])
            yog_boost = get_yogini_support(["Mars", "Mercury", "Bhramari", "Bhadrika"])
            return (
                f"{active_clocks}<br>"
                f"<b>Everyday Drive & Sibling Ties:</b> Steady personal enterprise and collaborative peer dynamics under {curr_md}-{curr_ad_lord} (until {curr_ad_end_fmt}).<br>"
                f"<b>High-Impact Enterprise & Collaborative Venture Window:</b> <span style='color:#b57c38;font-weight:700;'>{dr_st} – {dr_en}</span> under <b>{curr_md}-{dr_lord}</b> "
                f"(activating Bhratrukaraka {bk} and 3rd house courageous initiatives){yog_boost}."
            )

    elif code == "D12":
        # Parents
        par_lord, par_st, par_en = find_future_ad(["Sun", "Moon", h9_lord, h4_lord, "Jupiter"])
        yog_boost = get_yogini_support(["Sun", "Moon", "Jupiter", "Pingala", "Mangala", "Dhanya"])
        return (
            f"{active_clocks}<br>"
            f"<b>Ancestral Lineage & Parental Blessings:</b> Grounding moral wisdom and family protection under {curr_md}-{curr_ad_lord} (until {curr_ad_end_fmt}).<br>"
            f"<b>Family Milestone & Ancestral Fulfillment Window:</b> <span style='color:#b57c38;font-weight:700;'>{par_st} – {par_en}</span> under <b>{curr_md}-{par_lord}</b>, "
            f"bringing auspicious family harmony, paternal backing, and shared ancestral celebrations{yog_boost}."
        )

    else:
        # D1 Core
        core_lord, core_st, core_en = find_future_ad([ak, "Sun", "Jupiter", "Moon", "Mercury"])
        yog_boost = get_yogini_support(["Sun", "Jupiter", "Venus", "Siddha", "Dhanya", "Pingala"])
        return (
            f"{active_clocks}<br>"
            f"<b>Personal Constitution & Vitality:</b> Grounded self-realization under {curr_md}-{curr_ad_lord} (until {curr_ad_end_fmt}).<br>"
            f"<b>Personal Evolution & Clarity Window:</b> <span style='color:#b57c38;font-weight:700;'>{core_st} – {core_en}</span> under <b>{curr_md}-{core_lord}</b> "
            f"(activating Atmakaraka {ak} and core constitutional vitality){yog_boost}."
        )


def _determine_career_profile(
    d1_lagna: str,
    d1_h10_lord: str,
    d1_h10_lord_house: int,
    d10_lagna: str,
    d10_lord: str,
    d10_lord_house: int,
    strong_planets: list[str],
    amk: str,
) -> tuple[str, list[str], str]:
    """Computes chart-specific suited professional fields, executive archetype, and optimal work style."""
    prominent_planets = set()
    if d1_h10_lord:
        prominent_planets.add(d1_h10_lord)
    if d10_lord:
        prominent_planets.add(d10_lord)
    if amk:
        prominent_planets.add(amk)
    for sp in strong_planets:
        pname = sp.split()[0]
        prominent_planets.add(pname)

    suited_fields: list[str] = []
    archetype = "Strategic Professional & Advisory Specialist"
    work_style = "High-leverage analytical problem-solving and institutional guidance"

    # Identify fields by planetary confluence
    if any(p in prominent_planets for p in ("Mercury", "Rahu", "Saturn")):
        suited_fields.extend([
            "Technology & Software Engineering",
            "Data Analytics, AI & Advanced Systems",
            "Financial Technologies, Quantitative Research & Auditing",
        ])
    if any(p in prominent_planets for p in ("Jupiter", "Sun")):
        suited_fields.extend([
            "Strategic Consulting & Corporate Advisory",
            "Higher Education, Research & Policy Formulation",
            "Institutional Governance, Legal & Ethical Leadership",
        ])
    if any(p in prominent_planets for p in ("Mars", "Saturn")):
        suited_fields.extend([
            "Complex Infrastructure, Supply Chain & Operations",
            "Engineering, Real Estate Architecture & Project Leadership",
            "Defense, Energy & High-Stakes Operations",
        ])
    if any(p in prominent_planets for p in ("Venus", "Moon")):
        suited_fields.extend([
            "Design Architecture, Creative Direction & Media",
            "Healthcare Systems, Public Relations & Human Capital",
            "Luxury Goods, Brand Strategy & Client Experience",
        ])

    # Fallback to ensure distinct high-value fields
    if not suited_fields:
        suited_fields = [
            "Technology & Strategic Data Systems",
            "Executive Advisory & Management Consulting",
            "Financial Analysis, Auditing & Corporate Strategy",
            "Higher Academic Research & Applied Science",
        ]

    # De-duplicate while preserving order
    unique_fields = list(dict.fromkeys(suited_fields))[:4]

    # Archetype determination
    if d1_h10_lord_house in DUSTHANA or d10_lord_house in DUSTHANA:
        archetype = "Specialized Research, Advisory & Deep Technical Authority"
        work_style = "thrives in specialized research, advisory consulting, or deep technical architecture rather than routine bureaucratic desk work"
    elif "Sun" in prominent_planets or "Mars" in prominent_planets:
        archetype = "Executive Leadership, Operations & Institutional Direction"
        work_style = "commands executive accountability, organizational leadership, and high-impact operational strategy"
    elif "Jupiter" in prominent_planets or "Mercury" in prominent_planets:
        archetype = "Strategic Consultant, Knowledge Architect & Advisory Director"
        work_style = "excels in intellectual strategy, mentorship, policy analysis, and complex problem resolution"
    else:
        archetype = "Systems Architect & Strategic Implementation Specialist"
        work_style = "drives systematic execution, structured growth, and long-term institutional value creation"

    return archetype, unique_fields, work_style


def _determine_marriage_profile(
    d1_lagna: str,
    d1_h7_lord: str,
    d1_h7_lord_house: int,
    d9_lagna: str,
    d9_lord: str,
    d9_lord_house: int,
    dk: str,
) -> tuple[str, str, str]:
    """Computes chart-specific marriage partner nature, professional realm, and relationship dynamics."""
    key_ruler = d9_lord or d1_h7_lord or "Venus"

    partner_nature = "supportive, educated, and sensible"
    partner_realm = "professional, analytical, or educational domain"
    dynamics = "mutual intellectual respect and domestic stability"

    if key_ruler in ("Mercury", "Rahu"):
        partner_nature = "intellectually curious, articulate, adaptable, and business-savvy"
        partner_realm = "technology, finance, media, communications, or corporate consulting"
        dynamics = "stimulating intellectual companionship, active dialogue, and shared problem-solving"
    elif key_ruler in ("Jupiter", "Sun"):
        partner_nature = "principled, wise, mature, values-driven, and supportive of higher ideals"
        partner_realm = "education, legal, advisory, executive leadership, or public service"
        dynamics = "deep mutual trust, moral grounding, and shared life purpose (Bhagyodaya)"
    elif key_ruler in ("Venus", "Moon"):
        partner_nature = "gentle, culturally refined, empathetic, and aesthetically oriented"
        partner_realm = "creative arts, design, healthcare, hospitality, or client relations"
        dynamics = "warm emotional security, artistic appreciation, and a harmonious domestic sanctuary"
    elif key_ruler in ("Mars", "Saturn"):
        partner_nature = "pragmatic, hardworking, disciplined, loyal, and action-oriented"
        partner_realm = "engineering, operations, finance, real estate, or administrative governance"
        dynamics = "practical life building, enduring loyalty, and steady long-term stability"

    return partner_nature, partner_realm, dynamics


def build_divisional_insights(pc: dict) -> list[DivisionalInsight]:
    """Generates warm, highly specific, predictive observations for all 9 key vargas with collapsible proof and domain-specific dasha timing."""
    this_yr = date.today().year

    dob_str = str(pc.get("meta", {}).get("birth_date") or pc.get("meta", {}).get("dob") or "")
    birth_year = int(dob_str[:4]) if (len(dob_str) >= 4 and dob_str[:4].isdigit()) else 2000
    current_age = this_yr - birth_year

    DOMAIN_ID_MAP = {
        "D1": "domain-self",
        "D10": "domain-career",
        "D9": "domain-marriage",
        "D2": "domain-wealth",
        "D7": "domain-children",
        "D24": "domain-learning",
        "D4": "domain-home",
        "D30": "domain-health",
        "D3": "domain-siblings",
        "D12": "domain-parents",
    }
    codes = ["D1", "D10", "D9", "D2", "D7", "D24", "D4", "D30", "D3", "D12"]
    insights: list[DivisionalInsight] = []

    d1_lagna = _get_varga_lagna(pc, "D1")
    moon_sign = _get_varga_planet_sign(pc, "D1", "Moon")
    nakshatra = (pc.get("planets", {}).get("Moon", {}) or {}).get("nakshatra", "")

    # Jaimini Karakas
    jaimini = pc.get("jaimini", {})
    amk = jaimini.get("amk", "")
    dk = jaimini.get("dk", "")
    pk = jaimini.get("pk", "")

    # D1 placements for contextual cross-reference
    d1_planets = pc.get("planets", {})
    d1_h2_lord = SIGN_LORDS.get(house_sign(d1_lagna, 2), "") if d1_lagna else ""
    d1_h2_lord_house = d1_planets.get(d1_h2_lord, {}).get("house", 0) if d1_h2_lord else 0
    d1_h7_lord = SIGN_LORDS.get(house_sign(d1_lagna, 7), "") if d1_lagna else ""
    d1_h7_lord_house = d1_planets.get(d1_h7_lord, {}).get("house", 0) if d1_h7_lord else 0
    d1_h10_lord = SIGN_LORDS.get(house_sign(d1_lagna, 10), "") if d1_lagna else ""
    d1_h10_lord_house = d1_planets.get(d1_h10_lord, {}).get("house", 0) if d1_h10_lord else 0
    d1_h5_lord = SIGN_LORDS.get(house_sign(d1_lagna, 5), "") if d1_lagna else ""
    d1_h5_lord_house = d1_planets.get(d1_h5_lord, {}).get("house", 0) if d1_h5_lord else 0

    # Dasha context
    vim = pc.get("vimshottari", {})
    curr_md_obj = vim.get("current_md", {})
    curr_md = curr_md_obj.get("md_lord", "") if isinstance(curr_md_obj, dict) else str(curr_md_obj or "")
    md_seq = vim.get("sequence", [])
    if not curr_md:
        for s in md_seq:
            if s.get("status") == "current":
                curr_md = s.get("md_lord", "") or s.get("planet", "")
                break

    curr_ad_list = vim.get("current_md_antardashas", [])
    curr_ad_name = ""
    curr_ad_end = ""
    for ad in curr_ad_list:
        if ad.get("status") == "current" or ad.get("is_current"):
            curr_ad_name = ad.get("ad_lord") or ad.get("antardasha") or ""
            raw_end = str(ad.get("end") or "")
            curr_ad_end = _format_month_year(raw_end)
            break

    # Adulthood Mahadasha for milestones
    adulthood_md = ""
    adulthood_start_yr = 2036
    adulthood_end_yr = 2052
    for item in md_seq:
        s_date = str(item.get("start") or "")
        e_date = str(item.get("end") or "")
        lord_name = item.get("md_lord") or item.get("planet") or "Jupiter"
        if s_date and len(s_date) >= 4:
            s_yr = int(s_date[:4])
            if (s_yr - (this_yr - current_age)) >= 18 and not adulthood_md:
                adulthood_md = lord_name
                adulthood_start_yr = s_yr
                adulthood_end_yr = int(e_date[:4]) if (e_date and len(e_date) >= 4) else (s_yr + 16)
                break
    if not adulthood_md:
        adulthood_md = "Jupiter"

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
        all_placements = []

        for p in PLANETS:
            ps = _get_varga_planet_sign(pc, code, p)
            if not ps:
                continue
            h = ((sign_index(ps) - lagna_idx) % 12 + 1)
            dig = get_dignity(p, ps)
            dig_label = dig.replace('_', ' ').title() if dig else "Neutral"
            all_placements.append(f"{p} in {ps} (House {h}, {dig_label})")

            if dig in ("exalted", "moolatrikona", "own_sign"):
                strong_planets.append(f"{p} ({dig.replace('_', ' ').title()})")
            elif dig == "debilitated":
                debilitated_planets.append(f"{p} (Debilitated)")
            if h in DUSTHANA:
                trik_planets.append(f"{p} (House {h})")

        is_lord_in_trik = lord_house in DUSTHANA
        is_lord_debilitated = lord_dig == "debilitated"

        if is_lord_in_trik or is_lord_debilitated or len(debilitated_planets) >= 2 or len(trik_planets) >= 3:
            strength = "weak" if (is_lord_in_trik and is_lord_debilitated) else "mixed"
        elif lord_dig in ("exalted", "moolatrikona", "own_sign") and not is_lord_in_trik and len(strong_planets) >= 2:
            strength = "strong"
        else:
            strength = "mixed"

        timeline_str = _build_domain_specific_timeline(
            pc=pc,
            code=code,
            current_age=current_age,
            curr_md=curr_md,
            curr_ad_name=curr_ad_name,
            curr_ad_end=curr_ad_end,
            adulthood_md=adulthood_md,
            adulthood_start_yr=adulthood_start_yr,
        )

        headline, prediction, remedy = _interpret_varga_concrete(
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
            current_age=current_age,
            d1_h2_lord_house=d1_h2_lord_house,
            d1_h7_lord_house=d1_h7_lord_house,
            d1_h10_lord=d1_h10_lord,
            d1_h10_lord_house=d1_h10_lord_house,
            d1_h5_lord_house=d1_h5_lord_house,
            amk=amk,
            dk=dk,
        )

        # Build collapsible technical proof string
        proof_parts = [f"Ascendant (Lagna): <b>{v_lagna}</b>"]
        if lord and lord_sign:
            dig_str = f" ({lord_dig.replace('_', ' ').title()})" if lord_dig else ""
            proof_parts.append(f"Ruler: <b>{lord}</b> in {lord_sign} (House {lord_house}){dig_str}")
        if strong_planets:
            proof_parts.append(f"Dignified: <b>{', '.join(strong_planets)}</b>")
        if debilitated_planets:
            proof_parts.append(f"Debilitated: <b>{', '.join(debilitated_planets)}</b>")
        if trik_planets:
            proof_parts.append(f"Dusthana: <b>{', '.join(trik_planets)}</b>")

        evidence_str = " &nbsp;|&nbsp; ".join(proof_parts[:4]) + f"<br><span style='color:#666;font-size:0.74rem;'>All Placements: {'; '.join(all_placements)}</span>"

        insights.append(
            DivisionalInsight(
                code=code,
                name=meta.get("name", code),
                governs=meta.get("governs", ""),
                domain_id=DOMAIN_ID_MAP.get(code, f"domain-{code.lower()}"),
                lagna_sign=v_lagna,
                lord=lord,
                lord_sign=lord_sign,
                lord_house=lord_house,
                lord_dignity=lord_dig,
                strength=strength,
                headline=headline,
                prediction=prediction,
                timeline=timeline_str,
                remedy=remedy,
                evidence=evidence_str,
            )
        )

    return insights


def _interpret_varga_concrete(
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
    current_age: int,
    d1_h2_lord_house: int,
    d1_h7_lord_house: int,
    d1_h10_lord: str,
    d1_h10_lord_house: int,
    d1_h5_lord_house: int,
    amk: str,
    dk: str,
) -> tuple[str, str, str]:
    """Generates rich, highly specific, practical life interpretations for each divisional chart."""
    div_dict = pc.get("divisional", {})

    reading_parts: list[str] = []
    remedy_planet = lord
    remedy_type = "strengthen"
    remedy_reason = f"To Harmonize {lord}"

    if code == "D1":
        headline = f"Core Nature & Personal Vitality ({v_lagna} Rising)"
        reading_parts.append(
            f"Your foundational birth chart shows a thoughtful, perceptive, and adaptable nature (<b>{v_lagna} Rising</b>). "
            f"With your Moon in <b>{moon_sign} under {nakshatra}</b>, you have an alert mind that quickly absorbs ideas and notices subtle nuances around you."
        )
        if lord_house in DUSTHANA:
            reading_parts.append(
                f"Because your ruling planet (<b>{lord}</b>) is placed in the {ORDINALS.get(lord_house, '8th')} house, your journey builds deep resilience, research capability, and inner patience over time rather than instant outer results."
            )
            remedy_type = "dusthana"
            remedy_reason = f"To Support Your Ruling Planet ({lord})"
        else:
            reading_parts.append(
                f"Your ruling planet (<b>{lord}</b>) sits comfortably in the {ORDINALS.get(lord_house, '1st')} house, giving you steady physical vitality, natural independence, and self-confidence."
            )

    elif code == "D2":
        headline = f"Wealth, Savings & Financial Stability (Hora)"
        hora_nature = "strategic asset accumulation and compounding investments"
        if v_lagna in ("Leo", "Aries", "Sagittarius", "Gemini", "Libra", "Aquarius"):
            hora_nature = "active enterprise, self-made initiatives, leadership authority, and bold professional ventures"
        else:
            hora_nature = "resource preservation, liquid savings, real estate assets, and steady wealth compounding"

        reading_parts.append(
            f"This division maps your money instincts, asset retention, and long-term capital stability. "
            f"Your chart indicates that wealth compounds most reliably through <b>{hora_nature}</b> rather than speculative shortcuts."
        )
        if strong_planets:
            reading_parts.append(
                f"With favorable planetary backing ({', '.join(strong_planets)}) in this division, your capacity to hold resources, manage liquidity, and secure family independence strengthens steadily across your career years."
            )
        remedy_planet = "Jupiter"
        remedy_reason = "To Boost Wealth & Prosperity (Guru Upaya)"

    elif code == "D3":
        headline = f"Courage, Siblings & Everyday Initiative (Drekkana)"

        # 1. Courage & Enterprise (Parakrama)
        courage_str = "You possess strong natural courage, decisive execution, and the ability to take self-directed initiative on ambitious goals."
        if lord_house in (3, 6, 10, 11):
            courage_str = "Your chart confirms powerful upachaya drive (*Parakrama*), indicating that your determination and ability to overcome resistance grow stronger with every challenge."
        elif lord_house in DUSTHANA:
            courage_str = "Your personal enterprise develops through thoughtful strategy, research, and patient effort rather than hasty actions."

        # 2. Sibling Dynamics (Bhratru)
        sibling_str = "The Drekkana chart confirms supportive co-born relationships, mutual affection with siblings, and a collaborative spirit when working alongside close peers."
        if d1_h2_lord_house in (3, 9, 11, 1, 5) or "Mars" in [sp.split()[0] for sp in strong_planets]:
            sibling_str = "Governed by strong 3rd house indicators, your relationship with siblings brings mutual backing, shared family pride, and strong loyalty."
        elif d1_h2_lord_house in DUSTHANA:
            sibling_str = "Your chart favors cultivating independent self-reliance while maintaining respectful, mature communication with siblings and peers."

        # 3. Motor Skills & Physical Coordination
        motor_str = "You possess good physical coordination, manual dexterity, and the energy to carry projects across the finish line."

        # 4. Childhood Developmental context (only if child & afflicted)
        is_speech_sensitive = current_age < 18 and (d1_h2_lord_house in DUSTHANA or "Mercury" in [tp.split()[0] for tp in trik_planets] or "Mars" in [tp.split()[0] for tp in trik_planets])
        if is_speech_sensitive:
            development_str = (
                "In early childhood development, because 2nd and 3rd house indicators connect with sensitive areas in early years, "
                "this chart indicates a <b>temporary developmental pacing latency and heightened nervous sensitivity</b>. "
                "This is a transient foundational phase: structured speech exercises, physical coordination play, and supportive encouragement "
                "bring substantial, natural turnaround."
            )
            reading_parts.extend([
                f"The Drekkana division (D3) classically governs <b>courage (*Parakrama*), sibling bonds (*Bhratru*), physical motor vitality, and expressive throat coordination</b>.",
                courage_str,
                sibling_str,
                development_str
            ])
            remedy_planet = "Mercury"
            remedy_type = "dusthana"
            remedy_reason = "To Harmonize Speech & Motor Flow (Budha Upaya)"
        else:
            reading_parts.extend([
                f"The Drekkana division (D3) classically maps <b>personal courage (*Parakrama*), sibling relationships (*Bhratru*), everyday enterprise, and physical motor coordination</b>.",
                courage_str,
                sibling_str,
                motor_str
            ])
            remedy_planet = "Mars"
            remedy_reason = "To Boost Initiative & Courage (Mangal Upaya)"

    elif code == "D4":
        headline = f"Home, Land & Fixed Assets (Chaturthamsha)"
        reading_parts.append(
            f"This chart reflects domestic peace, home environment, and fixed property assets. "
            f"You possess strong long-term promise for owning comfortable residential property, reliable vehicles, and creating a stable, peaceful home sanctuary in adulthood."
        )
        if strong_planets:
            reading_parts.append(
                f"Fortified placements ({', '.join(strong_planets)}) in D4 support significant land appreciation and smooth property transactions."
            )
        remedy_planet = "Mars"
        remedy_reason = "To Energize Land & Property Assets (Bhoomi Upaya)"

    elif code == "D7":
        headline = f"Children, Family Lineage & Progeny (Saptamsha)"
        d7_moon = div_dict.get("D7", {}).get("Moon", "")
        d7_jup = div_dict.get("D7", {}).get("Jupiter", "")
        d7_ven = div_dict.get("D7", {}).get("Venus", "")

        d7_strong_list = []
        if d7_moon in ("Cancer", "Taurus"):
            d7_strong_list.append(f"Moon in {d7_moon}")
        if d7_jup in ("Sagittarius", "Pisces", "Cancer"):
            d7_strong_list.append(f"Jupiter in {d7_jup}")
        if d7_ven in ("Taurus", "Libra", "Pisces"):
            d7_strong_list.append(f"Venus in {d7_ven}")
        if "own_sign" in lord_dig or "exalted" in lord_dig:
            d7_strong_list.append(f"{lord} in {lord_sign} ({lord_dig.replace('_', ' ').title()})")

        if d7_strong_list:
            guardians_str = f"The key guardians of progeny ({', '.join(d7_strong_list)}) are deeply fortified in this chart."
            reading_parts.append(
                f"This division reveals an <b>exceptionally fertile, blessed, and strong foundational promise for children and family continuation</b>. "
                f"{guardians_str} "
                f"Classical confirmation affirms joyful, healthy children and family happiness that unfolds naturally after marriage in adulthood."
            )
        else:
            reading_parts.append(
                f"This chart confirms supportive potential for children and family continuation, bringing deep emotional joy, mutual affection, and fulfillment through parenthood."
            )
        remedy_planet = "Jupiter"
        remedy_reason = "To Bless Progeny & Family Growth (Santan Gopal Upaya)"

    elif code == "D9":
        headline = f"Marriage, Life Partner & Soul Purpose (Navamsha)"
        partner_nature, partner_realm, dynamics = _determine_marriage_profile(
            d1_lagna=d1_lagna,
            d1_h7_lord=SIGN_LORDS.get(house_sign(d1_lagna, 7), ""),
            d1_h7_lord_house=d1_h7_lord_house,
            d9_lagna=v_lagna,
            d9_lord=lord,
            d9_lord_house=lord_house,
            dk=dk,
        )
        reading_parts.append(
            f"The Navamsha division maps life partnership, marital harmony, and inner destiny (Bhagyodaya). "
            f"Your chart indicates a <b>{partner_nature}</b> life partner, likely connected with <b>{partner_realm}</b>. "
            f"The relationship provides {dynamics}, bringing emotional stability, shared values, and mutual life elevation in adulthood."
        )
        remedy_planet = "Venus"
        remedy_reason = "To Foster Harmony in Relationships (Shukra Upaya)"

    elif code == "D10":
        headline = f"Career, Leadership & Professional Status (Dasamsha)"
        archetype, suited_fields, work_style = _determine_career_profile(
            d1_lagna=d1_lagna,
            d1_h10_lord=d1_h10_lord,
            d1_h10_lord_house=d1_h10_lord_house,
            d10_lagna=v_lagna,
            d10_lord=lord,
            d10_lord_house=lord_house,
            strong_planets=strong_planets,
            amk=amk,
        )
        fields_bullet = ", ".join([f"<b>{f}</b>" for f in suited_fields])
        reading_parts.append(
            f"Your professional karma operates as an <b>{archetype}</b>. Your natural work style {work_style}.<br><br>"
            f"<b>Optimal High-Growth Career Fields:</b> Your planetary confluence indicates maximum success and recognition in {fields_bullet}. "
            f"Gaining specialized subject mastery early paves the way for significant executive respect and leadership authority."
        )
        remedy_planet = "Sun"
        remedy_type = "dusthana" if d1_h10_lord_house in DUSTHANA else "strengthen"
        remedy_reason = "To Strengthen Professional Authority (Surya Upaya)"

    elif code == "D12":
        headline = f"Family Roots & Parental Blessings (Dwadashamsha)"
        reading_parts.append(
            f"This chart reflects family heritage, parental affection, and ancestral protection. "
            f"You carry strong moral grounding and blessings from parents. Respecting family elders and honoring family traditions brings positive energetic support throughout your life."
        )
        if strong_planets:
            reading_parts.append(
                f"Fortified placements ({', '.join(strong_planets)}) in D12 indicate noble lineage and deep parental blessings."
            )
        remedy_planet = "Sun"
        remedy_reason = "To Honor Ancestral Blessings (Pitru Upaya)"

    elif code == "D24":
        headline = f"Education, Memory & Intellectual Mastery (Chaturvimshamsha)"
        reading_parts.append(
            f"The D24 chart confirms strong conceptual grasping power, analytical thinking, and the ability to master complex disciplines. "
            f"With structured, distraction-free study habits, you can excel in technical, scientific, legal, or management programs and competitive certifications."
        )
        if strong_planets:
            reading_parts.append(
                f"Fortified planets ({', '.join(strong_planets)}) in D24 indicate exceptional memory retention, academic distinction, and intellectual authority."
            )
        remedy_planet = "Mercury"
        remedy_reason = "To Sharpen Memory & Academic Focus (Saraswati Upaya)"

    elif code == "D30":
        headline = f"Health Sensitivities & Inner Resilience (Trimsamsha)"
        d30_merc = div_dict.get("D30", {}).get("Mercury", "")
        d30_rahu = div_dict.get("D30", {}).get("Rahu", "")
        is_neuro_sensitive = current_age < 18 and d30_merc and d30_rahu and d30_merc == d30_rahu
        if is_neuro_sensitive:
            reading_parts.append(
                f"This chart helps identify latent physical sensitivities and how you bounce back from stress. "
                f"The presence of sensitive planetary placements (Mercury and Rahu closely aligned in {d30_merc}) highlights <b>nervous system sensitivity, sensory fatigue, and developmental speech vulnerability in early years</b>. "
                f"Your chart carries strong inherent recovery power: maintaining regular sleep routines, minimizing digital overstimulation, and gentle spiritual remedies help you overcome childhood challenges and build lasting physical and mental strength."
            )
            remedy_planet = "Mercury"
            remedy_type = "dusthana"
            remedy_reason = "To Fortify Nervous System & Vitality (Maha Mrityunjaya Upaya)"
        else:
            reading_parts.append(
                f"The Trimsamsha confirms strong natural immunity and the inner fortitude to bounce back rapidly from physical or emotional fatigue through balanced daily habits."
            )
            if trik_planets:
                reading_parts.append(
                    f"Paying attention to bodily signals during dusthana transits ({', '.join(trik_planets)}) prevents minor exhaustion."
                )
            remedy_planet = "Saturn"
            remedy_reason = "To Fortify Inner Immunity & Resilience (Shani Upaya)"

    prediction = " ".join(reading_parts)

    # Targeted Remedy Text
    if remedy_planet and remedy_planet in PLANET_REMEDIES:
        rem_text = PLANET_REMEDIES[remedy_planet].get(remedy_type, PLANET_REMEDIES[remedy_planet]["strengthen"])
        remedy = f"<b>{remedy_reason}:</b> {rem_text}"
    else:
        remedy = "Maintain regular spiritual grounding, meditation, and mindful daily habits."

    return headline, prediction, remedy


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
                "Your birth chart carries classical foundational strengths where focused personal effort and disciplined habits "
                "consistently unlock meaningful opportunities across major life chapters."
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
      - Full cards for D1 (Self), D2 (Wealth), D3 (Speech/Motor/Drive), D12 (Parents).
      - Remedy boxes blurred with lock overlay.
      - Locked teaser preview for D7 (Kids), D9 (Marriage), D10 (Career), D24 (Education), D30 (Hardships).
    Paid tier:
      - All 9 divisional cards rendered in full depth with strengths, domain-specific timelines, unblurred remedies, and collapsible proof.
    """
    insights = build_divisional_insights(pc)
    summary_108 = get_108_snapshot_summary_paragraph(pc)

    div_cards_html = []
    teaser_items = []

    for ins in insights:
        pill_cls = "up" if ins.strength == "strong" else "down" if ins.strength == "weak" else "mixed"
        pill_lbl = "Well Supported" if ins.strength == "strong" else "Needs Care" if ins.strength == "weak" else "Constructive / Active"
        border_color = "#1c6b45" if ins.strength == "strong" else "#a3341f" if ins.strength == "weak" else "#8a6a1f"

        is_free_allowed = ins.code in FREE_ALLOWED_VARGAS

        if paid or is_free_allowed:
            # Dasha Timeline Box (Domain Specific)
            timeline_box = ""
            if ins.timeline:
                timeline_box = (
                    f'  <div style="background:#fcfbf8;border-left:3px solid #b57c38;padding:8px 12px;border-radius:6px;margin:8px 0 10px;font-size:0.84rem;line-height:1.5;color:#2c3140;">\n'
                    f'    {ins.timeline}\n'
                    f'  </div>\n'
                )

            # Remedy display: Clear if paid, blurred with lock overlay if free
            if paid:
                remedy_box = (
                    f'  <div style="background:#f9f8f5;border-left:3px solid #1c6b45;padding:8px 12px;border-radius:6px;margin:8px 0 10px;font-size:0.84rem;line-height:1.45;color:#4a453c;">\n'
                    f'    <b>Targeted Vedic Upaya:</b> {ins.remedy}\n'
                    f'  </div>\n'
                )
            else:
                remedy_box = (
                    f'  <div class="lock-wrap" style="margin:8px 0 10px;border-radius:8px;">\n'
                    f'    <div class="lock-blur" style="padding:8px 12px;font-size:0.84rem;line-height:1.45;">\n'
                    f'      <b>Targeted Vedic Upaya:</b> {ins.remedy}\n'
                    f'    </div>\n'
                    f'    <div class="lock-over">\n'
                    f'      <span class="lock-chip" style="font-size:0.65rem;padding:4px 10px;">🔒 Remedial Action in Full Reading</span>\n'
                    f'    </div>\n'
                    f'  </div>\n'
                )

            # Collapsible Proof Drawer
            proof_drawer = (
                f'  <details style="margin-top:10px;border-top:1px solid #eeeae3;padding-top:8px;font-size:0.78rem;color:#7a756c;line-height:1.45;">\n'
                f'    <summary style="cursor:pointer;font-weight:600;color:#1f2430;">Technical Astrological Proof ({html.escape(ins.name)})</summary>\n'
                f'    <div style="padding-top:6px;color:#444;">\n'
                f'      {ins.evidence}\n'
                f'    </div>\n'
                f'  </details>\n'
            )

            card = (
                f'<article class="card div-card" id="{ins.domain_id}" style="margin-bottom:16px;border-left:4px solid {border_color};background:#fff;border-radius:12px;padding:16px 18px;box-shadow:0 2px 8px rgba(0,0,0,0.03);">\n'
                f'  <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px;">\n'
                f'    <span style="font-size:0.7rem;letter-spacing:0.12em;text-transform:uppercase;font-weight:700;color:#6a7080;">{html.escape(ins.code)} · {html.escape(ins.governs)}</span>\n'
                f'    <span class="pill {pill_cls}" style="font-size:0.65rem;font-weight:700;padding:2px 8px;border-radius:99px;">{pill_lbl}</span>\n'
                f'  </div>\n'
                f'  <h3 style="font-family:Georgia,serif;font-size:1.08rem;margin:4px 0 8px;color:#1f2430;font-weight:600;">{html.escape(ins.headline)}</h3>\n'
                f'  <div style="margin:0 0 10px;font-size:0.9rem;line-height:1.58;color:#2c3140;">{ins.prediction}</div>\n'
                f'{timeline_box}'
                f'{remedy_box}'
                f'{proof_drawer}'
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
            f'</div>\n'
        )

    # 108 Rule Snapshot Card
    snapshot_108_html = (
        f'<article class="card snapshot-108-card" style="margin-bottom:16px;background:#fbfbf9;border:1px solid #e8e4dc;border-left:4px solid #b57c38;border-radius:12px;padding:16px 18px;box-shadow:0 2px 8px rgba(0,0,0,0.03);">\n'
        f'  <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px;">\n'
        f'    <span style="font-size:0.7rem;letter-spacing:0.12em;text-transform:uppercase;font-weight:700;color:#7a4b18;">Classical Confluence Synthesis</span>\n'
        f'    <span class="pill up" style="font-size:0.65rem;font-weight:700;padding:2px 8px;border-radius:99px;">Static Promise</span>\n'
        f'  </div>\n'
        f'  <h3 style="font-family:Georgia,serif;font-size:1.05rem;margin:4px 0 8px;color:#1f2430;font-weight:600;">Foundational Astrological Baseline</h3>\n'
        f'  <p style="margin:0;font-size:0.9rem;line-height:1.6;color:#2c3140;">{summary_108}</p>\n'
        f'</article>\n'
    )

    return f"{snapshot_108_html}\n{''.join(div_cards_html)}\n{teaser_html}"
