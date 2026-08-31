#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vedic_consultation_reading.py — Generalized Vedic Mind State & Timeline Engine

Algorithmic, zero-overfitting astrologer mind-reading engine based on:
1. Active Chandra Naadi Trigger (Transit Moon contacting natal planets & Bhavas).
2. Current Dasha/Antardasha mental polarity vs Transit Moon.
3. 6-Month Timeline & Structural testing via slow-moving transits (Saturn, Rahu, Ketu).
4. Definitive turning-point forecasting with exact dates.
5. Static Natal Foundations (BNN Directional Trines, Jaimini Chara Karakas, Ashtakavarga).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import swisseph as swe

from astro_precompute import (
    NAKSHATRAS,
    SIGNS,
    SIGN_LORDS,
    VIMSH_LORDS,
    VIMSH_YEARS,
    build_vimshottari_from_moon,
    degree_to_nakshatra,
    get_dignity,
    house_from_lagna,
    sign_index,
)

PLANET_KARAKAS = {
    "Sun": "authority, leadership, father, government, executive status, self-reliance, physical vitality",
    "Moon": "emotional peace, mother, mind, residence, fluid cash, public relations, domestic harmony",
    "Mars": "land, real estate, courage, engineering, machinery, younger siblings, physical stamina, disputes",
    "Mercury": "intellectual strategy, commercial agreements, software, auditing, mathematics, trade, speech",
    "Jupiter": "wisdom, expansion, finance, preceptors, progeny, legal ethics, long-term wealth, spirituality",
    "Venus": "luxury, spouse, vehicles, aesthetic arts, liquid assets, partnerships, high-value comforts",
    "Saturn": "career duty, structural discipline, labor, delayed perseverance, endurance, legal responsibility",
    "Rahu": "unconventional innovation, foreign affairs, mass ambition, digital tech, unexpected breakthroughs",
    "Ketu": "spiritual wisdom, detachment, legal arbitration, medical analysis, pruning dependencies, autonomy",
}

BHAVA_THEMES = {
    1: ("Self & Vitality", "personal direction, physical vitality, self-identity, and fundamental life choices"),
    2: ("Wealth & Speech", "liquid savings, family assets, speech impact, and commercial intake"),
    3: ("Initiatives & Communication", "independent ventures, courage, communication, contracts, and digital initiatives"),
    4: ("Home & Inner Peace", "domestic stability, mother's welfare, property/vehicles, and emotional sanctuary"),
    5: ("Intellect & Creativity", "strategic creativity, speculation, children, creative projects, and intuitive intelligence"),
    6: ("Debts, Health & Competition", "overcoming obstacles, solving workplace disputes, health regimens, and daily execution"),
    7: ("Partnerships & Public Status", "business collaborations, marital dynamics, client negotiations, and public dealings"),
    8: ("Transformation & Deep Research", "unearned assets, deep research, systemic overhauls, hidden liabilities, and longevity"),
    9: ("Fortune, Father & Higher Vision", "paternal affairs, higher wisdom, long-distance expansion, and foundational philosophy"),
    10: ("Karma, Career & Authority", "professional leadership, enterprise building, corporate standing, and career autonomy"),
    11: ("Gains, Ambition & Network", "realization of major ambitions, professional network, large financial gains, and alliances"),
    12: ("Expenditure, Solitude & Expansion", "foreign connections, strategic solitude, substantial investments, and spiritual release"),
}

BNN_DIRECTIONS = {
    "Aries": "East (Dharma / Action)", "Leo": "East (Dharma / Action)", "Sagittarius": "East (Dharma / Action)",
    "Taurus": "South (Artha / Wealth)", "Virgo": "South (Artha / Wealth)", "Capricorn": "South (Artha / Wealth)",
    "Gemini": "West (Kama / Desire)", "Libra": "West (Kama / Desire)", "Aquarius": "West (Kama / Desire)",
    "Cancer": "North (Moksha / Knowledge)", "Scorpio": "North (Moksha / Knowledge)", "Pisces": "North (Moksha / Knowledge)",
}


def _get_planet_positions_at_date(dt: datetime) -> dict:
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute / 60.0)
    mapping = {
        "Sun": swe.SUN,
        "Moon": swe.MOON,
        "Mars": swe.MARS,
        "Mercury": swe.MERCURY,
        "Jupiter": swe.JUPITER,
        "Venus": swe.VENUS,
        "Saturn": swe.SATURN,
        "Rahu": swe.MEAN_NODE,
    }
    res = {}
    for p, pid in mapping.items():
        pos, _ = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL)
        lon = pos[0]
        s_idx = int(lon // 30) % 12
        deg = lon % 30
        res[p] = {"sign": SIGNS[s_idx], "degree": deg, "abs_degree": lon, "sign_idx": s_idx}

    k_lon = (res["Rahu"]["abs_degree"] + 180.0) % 360.0
    k_s_idx = int(k_lon // 30) % 12
    res["Ketu"] = {"sign": SIGNS[k_s_idx], "degree": k_lon % 30, "abs_degree": k_lon, "sign_idx": k_s_idx}
    return res


def generate_consultation_reading(
    pc: dict,
    *,
    analysis_datetime: datetime | None = None,
    gender: str = "male",
    lang: str = "en",
) -> dict:
    """
    Synthesizes a deep, generalized consultation-level astrological reading:
    1. Exact mind state & dilemmas happening right now (Transit Moon activation ONLY).
    2. Exact timeline of the last 6 months (Dasha shift & structural tests).
    3. How resilience was built and the turning-point roadmap ahead.
    4. Static Natal Foundations (BNN Triplicities, Jaimini Chara Karakas, Ashtakavarga).
    """
    if analysis_datetime is None:
        analysis_datetime = datetime.now()

    now = analysis_datetime
    six_months_ago = now - timedelta(days=180)

    lagna_sign = pc.get("meta", {}).get("lagna_sign", "Aries")
    client_name = pc.get("meta", {}).get("client", "Native")
    dob_str = pc.get("meta", {}).get("dob", "1990-01-01")
    dob_date = datetime.strptime(dob_str, "%Y-%m-%d").date()

    planets = pc.get("planets", {})
    natal_moon_sign = planets.get("Moon", {}).get("sign", "Aries")
    natal_moon_nak = planets.get("Moon", {}).get("nakshatra", "Ashwini")
    natal_moon_deg_in_nak = planets.get("Moon", {}).get("degree_in_nakshatra", 0.0)

    # Calculate current and past Dasha
    vim = build_vimshottari_from_moon(natal_moon_nak, natal_moon_deg_in_nak, dob_date)
    curr_md = vim.get("current_md", {})
    antardashas = vim.get("current_md_antardashas", [])

    curr_ad = next((a for a in antardashas if a["status"] == "current"), {})
    next_ad = next((a for a in antardashas if a["status"] == "future"), {})

    # Check which Antardasha was active 6 months ago
    six_mo_str = six_months_ago.strftime("%Y-%m-%d")
    past_ad = next((a for a in antardashas if a.get("start", "") <= six_mo_str <= a.get("end", "")), None)
    if past_ad is None:
        past_ad = {"ad_lord": "Previous Sub-cycle", "end": curr_ad.get("start", "")}

    # Transits Now
    transits_now = _get_planet_positions_at_date(now)
    t_moon_sign = transits_now["Moon"]["sign"]
    t_moon_deg = transits_now["Moon"]["degree"]
    t_sat_sign = transits_now["Saturn"]["sign"]
    t_rahu_sign = transits_now["Rahu"]["sign"]
    t_ketu_sign = transits_now["Ketu"]["sign"]
    t_jup_sign = transits_now["Jupiter"]["sign"]

    # ══════════════════════════════════════════════════════════════════
    # 1. WHAT IS IN YOUR MIND RIGHT NOW (Real-Time Trigger ONLY)
    # ══════════════════════════════════════════════════════════════════
    t_moon_house_from_lagna = house_from_lagna(t_moon_sign, lagna_sign)
    t_moon_house_from_moon = house_from_lagna(t_moon_sign, natal_moon_sign)

    # Natal planets conjunct Transit Moon
    contacted_planets = [p for p, d in planets.items() if d.get("sign") == t_moon_sign]
    contacted_karakas = [PLANET_KARAKAS.get(p, "") for p in contacted_planets]

    bhava_title, bhava_meaning = BHAVA_THEMES.get(t_moon_house_from_lagna, ("Core Life Themes", "essential priorities"))

    mind_state_points = []

    # Primary Preoccupation
    if contacted_planets:
        p_names = " & ".join(contacted_planets)
        p_desc = ", ".join(contacted_karakas)
        mind_state_points.append(
            f"<b>The Core Preoccupation ({bhava_title} &mdash; House {t_moon_house_from_lagna}):</b> "
            f"The transiting Moon is directly contacting your natal <b>{p_names}</b>. Your mind is hyper-focused on "
            f"{p_desc}. You are actively evaluating strategic decisions, commercial or intellectual agreements, and "
            f"seeking concrete autonomy in this domain rather than remaining dependent on external circumstances."
        )
    else:
        mind_state_points.append(
            f"<b>The Core Preoccupation ({bhava_title} &mdash; House {t_moon_house_from_lagna}):</b> "
            f"The transiting Moon is illuminating your House {t_moon_house_from_lagna} from Lagna. Your immediate "
            f"thoughts are centered on {bhava_meaning}, sorting out pending decisions and establishing clear priorities."
        )

    # Psychological Polarity & Tension (Dasha Lord vs Transit Moon)
    md_lord = curr_md.get("md_lord", "Jupiter")
    ad_lord = curr_ad.get("ad_lord", "Ketu")

    if ad_lord in ["Ketu", "Saturn"]:
        psych_tension = (
            f"While your intellect is actively formulating progressive strategies, the running <b>{md_lord}-{ad_lord}</b> "
            f"cycle introduces an underlying feeling of detachment and healthy skepticism. You are questioning superficial "
            f"collaborations and feeling impatient with slow external validation or associates who cannot keep pace with your vision."
        )
    elif ad_lord in ["Rahu"]:
        psych_tension = (
            f"The active <b>{md_lord}-Rahu</b> sub-period fuels an intense craving for rapid expansion and technological/mass "
            f"breakthroughs, but simultaneously creates anxiety about ensuring long-term stability and avoiding premature commitments."
        )
    elif ad_lord in ["Venus", "Jupiter", "Mercury"]:
        psych_tension = (
            f"The active <b>{md_lord}-{ad_lord}</b> sub-period provides high intellectual clarity and diplomatic elegance, "
            f"motivating you to build high-value alliances, optimize liquid assets, and elevate your personal standing."
        )
    else:
        psych_tension = (
            f"The active <b>{md_lord}-{ad_lord}</b> cycle focuses your mental bandwidth directly on establishing authority, "
            f"vitality, and decisive execution."
        )

    mind_state_points.append(f"<b>The Psychological Tension (Ambition vs. Alignment):</b> {psych_tension}")

    # Axis Dynamic (From Natal Moon)
    if t_moon_house_from_moon in [1, 7]:
        axis_note = "Because the transiting Moon aligns directly on your 1st/7th axis from natal Moon, you are weighing personal independence against the demands of key partnerships and public commitments."
    elif t_moon_house_from_moon in [4, 10]:
        axis_note = "Because the transiting Moon activates the 4th/10th axis from natal Moon, you are actively balancing demanding career ambitions against your need for domestic sanctuary, family wellbeing, and peace of mind."
    else:
        axis_note = f"Operating from House {t_moon_house_from_moon} from your natal Moon, this transit encourages practical problem-solving, financial accounting, and clearing pending backlogs."

    mind_state_points.append(f"<b>Equilibrium Focus:</b> {axis_note}")

    # ══════════════════════════════════════════════════════════════════
    # 2. WHAT HAPPENED IN THE LAST 6 MONTHS (Timeline & Confidence Building)
    # ══════════════════════════════════════════════════════════════════
    timeline_points = []

    # Check if Dasha shifted recently
    ad_start_raw = curr_ad.get("start", "")
    ad_start_dt = datetime.strptime(ad_start_raw[:10], "%Y-%m-%d") if ad_start_raw else now
    shifted_recently = (now - ad_start_dt).days <= 240

    if shifted_recently:
        shift_month_str = ad_start_dt.strftime("%B %Y")
        timeline_points.append(
            f"<b>Major Dasha Shift ({shift_month_str}):</b> You transitioned into the <b>{md_lord} Mahadasha &mdash; {ad_lord} Antardasha</b>. "
            f"This marked a definitive pivot where old, conventional ways of operating began feeling spiritually dry or misaligned. "
            f"You felt a strong urge to clean the slate, eliminate distractions, and focus exclusively on core, authentic mastery."
        )
    else:
        timeline_points.append(
            f"<b>Dasha Maturation ({md_lord} &mdash; {ad_lord}):</b> Over the past 6 months, you have been navigating the deeper "
            f"lessons of {ad_lord} Antardasha, demanding rigorous self-discipline, auditing relationships, and refining personal systems."
        )

    # Slow Moving Transit Pressure (Saturn & Rahu/Ketu)
    sat_h = house_from_lagna(t_sat_sign, lagna_sign)
    sat_theme, sat_desc = BHAVA_THEMES.get(sat_h, ("Career & Duty", "structural responsibilities"))

    # Ashtakavarga SAV points for transit Saturn sign
    sav_list = pc.get("ashtakavarga", {}).get("sav", [])
    sat_s_idx = SIGNS.index(t_sat_sign) if t_sat_sign in SIGNS else 0
    sat_sav_pts = sav_list[sat_s_idx] if isinstance(sav_list, list) and len(sav_list) > sat_s_idx else 28

    if sat_sav_pts >= 30:
        sav_note = f"Holding {sat_sav_pts} SAV bindus, this sign gives solid ground traction and delivers strong material backing."
    elif sat_sav_pts >= 25:
        sav_note = f"Holding {sat_sav_pts} SAV bindus, this sign is workable but requires disciplined, methodical pacing."
    else:
        sav_note = f"Holding {sat_sav_pts} SAV bindus, this sign requires extra proof stacks, patience, and rigorous verification."

    timeline_points.append(
        f"<b>Structural Testing via Saturn (House {sat_h} &mdash; {t_sat_sign}):</b> Saturn transiting your House {sat_h} has "
        f"imposed heavy workloads, accountability, and systemic restructuring ({sav_note}). You have had to double down on rigorous execution, "
        f"building robust foundations with zero room for superficial shortcuts."
    )

    rahu_h = house_from_lagna(t_rahu_sign, lagna_sign)
    rahu_theme, rahu_desc = BHAVA_THEMES.get(rahu_h, ("Higher Purpose", "expanding horizons"))
    timeline_points.append(
        f"<b>Karmic Re-evaluation via Rahu/Ketu (House {rahu_h}/{house_from_lagna(t_ketu_sign, lagna_sign)}):</b> "
        f"Rahu in House {rahu_h} stimulated intense questioning of traditional rules and external dependencies, sparking a "
        f"powerful ambition to establish your own distinct legacy and intellectual sovereignty."
    )

    # How Resilience Was Built
    resilience_summary = (
        f"Despite moments of isolation or slow external applause over the last 6 months, you successfully distilled your "
        f"core strengths, established robust technical/operational frameworks, and learned that your own self-reliance is your "
        f"most enduring asset."
    )
    timeline_points.append(f"<b>How Real Strength Was Built:</b> {resilience_summary}")

    # ══════════════════════════════════════════════════════════════════
    # 3. ROADMAP AHEAD & EXACT TURNING POINT
    # ══════════════════════════════════════════════════════════════════
    ad_end_raw = curr_ad.get("end", "")
    ad_end_dt = datetime.strptime(ad_end_raw[:10], "%Y-%m-%d") if ad_end_raw else now
    ad_end_str = ad_end_dt.strftime("%d %b %Y")

    next_lord = next_ad.get("ad_lord", "Next Period")
    next_end_raw = next_ad.get("end", "")
    next_end_str = datetime.strptime(next_end_raw[:10], "%Y-%m-%d").strftime("%d %b %Y") if next_end_raw else ""

    next_planet_data = planets.get(next_lord, {})
    next_dig = next_planet_data.get("dignity", "neutral_sign")
    next_house = next_planet_data.get("house", 1)

    if next_dig in ["exalted", "own_sign", "moolatrikona"]:
        forecast_grade = "Highly Auspicious / Golden Era"
        forecast_desc = (
            f"Your natal {next_lord} is strongly dignified ({next_dig}) in House {next_house}. When this sub-period begins, "
            f"the silent efforts and systems built during the current cycle will convert into massive material prosperity, "
            f"elevated status, and widespread recognition."
        )
    elif next_lord in ["Venus", "Jupiter", "Mercury", "Sun"]:
        forecast_grade = "Expansive & Fruitful Phase"
        forecast_desc = (
            f"Activating {next_lord} in House {next_house} unlocks rapid progress, supportive alliances, financial liquidity, "
            f"and positive milestone celebrations."
        )
    else:
        forecast_grade = "Structured & Transformative Phase"
        forecast_desc = (
            f"Activating {next_lord} in House {next_house} brings major structural maturity, long-term stability, and legal/institutional authority."
        )

    roadmap_points = [
        f"<b>Current Phase Strategy (until {ad_end_str}):</b> You are in the final refinement window of {ad_lord}. Use this period to consolidate systems, settle pending liabilities, and avoid uncollateralized speculative bets.",
        f"<b>The Turning Point ({ad_end_str} to {next_end_str}):</b> Transition into <b>{next_lord} Antardasha</b> &mdash; <span class='phase-pill positive'>{forecast_grade}</span><br>{forecast_desc}",
    ]

    # ══════════════════════════════════════════════════════════════════
    # 4. STATIC NATAL FOUNDATION PILLARS (BNN Trines, Jaimini, Dignities)
    # ══════════════════════════════════════════════════════════════════
    foundation_points = []

    # Dignity highlights
    for p, d in planets.items():
        h = d.get("house", 1)
        s = d.get("sign", "")
        dig = d.get("dignity", "neutral")
        if dig in ["exalted", "own_sign", "moolatrikona"]:
            foundation_points.append(
                f"<span class='tag'>Core Pillar</span><b>{p} in House {h} ({s}):</b> Holds strong status ({dig}), serving as an enduring powerhouse for {p} life themes."
            )
        elif dig in ["debilitated"]:
            foundation_points.append(
                f"<span class='tag'>Karmic Growth</span><b>{p} in House {h} ({s}):</b> Operates through initial friction; transforms into solid authority through patient expertise."
            )

    # Multi-planet clusters
    by_house: dict[int, list[str]] = {}
    for p, d in planets.items():
        by_house.setdefault(d.get("house", 1), []).append(p)

    for h_num, p_list in sorted(by_house.items()):
        if len(p_list) >= 2:
            p_str = " + ".join(p_list)
            sign_name = planets[p_list[0]].get("sign", "")
            foundation_points.append(
                f"<span class='tag'>House {h_num} Powerhouse ({sign_name})</span><b>{p_str} Cluster:</b> Unifies {p_str} energies into a major life driving force in House {h_num} domains."
            )

    # BNN 1-5-9 Directional Confluence
    bnn_trines: dict[str, list[str]] = {"East": [], "South": [], "West": [], "North": []}
    for p_k, p_info in planets.items():
        s_name = p_info.get("sign", "Aries")
        d_key = BNN_DIRECTIONS.get(s_name, "East").split()[0]
        bnn_trines[d_key].append(p_k)

    sat_trine_key = BNN_DIRECTIONS.get(planets.get("Saturn", {}).get("sign", "Aries"), "North").split()[0]
    sat_confluence = bnn_trines.get(sat_trine_key, [])
    if len(sat_confluence) >= 2:
        c_str = " + ".join(sat_confluence)
        foundation_points.append(
            f"<span class='tag'>BNN 1-5-9 Triplicity ({sat_trine_key} Trine)</span><b>Karma Confluence ({c_str}):</b> In Bhrigu Nandi Nadi, your Karma Karaka Saturn operates in direct mutual triplicity with {c_str}, unifying professional duty, analytical acumen, and commercial wealth into your permanent karmic signature."
        )

    # Jaimini Chara Karakas
    ck_list = pc.get("cara_karakas", {}).get("karakas", [])
    ak_entry = next((k for k in ck_list if k.get("role") in ["Atmakarak", "Atmakaraka"]), None)
    amk_entry = next((k for k in ck_list if k.get("role") in ["Amatyakarak", "Amatyakaraka"]), None)

    if ak_entry and amk_entry:
        ak_p = ak_entry.get("planet")
        ak_s = ak_entry.get("sign")
        ak_h = ak_entry.get("house")
        ak_dig = ak_entry.get("dignity", "")

        amk_p = amk_entry.get("planet")
        amk_s = amk_entry.get("sign")
        amk_h = amk_entry.get("house")

        foundation_points.append(
            f"<span class='tag'>Jaimini Soul & Career Compass</span><b>Atmakaraka ({ak_p} in House {ak_h}, {ak_s}) &mdash; Amatyakaraka ({amk_p} in House {amk_h}, {amk_s}):</b> Your Soul Karaka {ak_p} holds {ak_dig} status, confirming that ultimate life fulfillment comes through high-caliber creative and ethical autonomy, while Career Director {amk_p} directs your output toward independent executive authority and advisory roles."
        )

    return {
        "meta": {
            "client": client_name,
            "dob": dob_str,
            "gender": gender,
            "lagna": lagna_sign,
            "moon_sign": natal_moon_sign,
            "analysis_datetime": str(analysis_datetime),
        },
        "mind_state": mind_state_points,
        "past_6_months": timeline_points,
        "roadmap_ahead": roadmap_points,
        "foundation_points": foundation_points,
    }
