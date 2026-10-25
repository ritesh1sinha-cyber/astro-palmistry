"""Chandra Naadi, read for the PRESENT moment of any question (every life area, not only health).

Chandra Naadi's strength is the live picture: where the transiting Moon is touching the birth chart right
now, and whether this is a moment the method treats as sensitive. For every question this module reads:

    contacts     which natal planets the transit Moon conjoins or aspects (core methodology), and which of
                 those carry THIS question (its natural indicators, the house ruler, the planets in the
                 question's houses and the rulers of its supporting houses). A relevant planet that is
                 well placed helps; one that is under strain brings pressure.
    cautions     Chandrashtama (Moon 8th from the birth Moon), the Moon over the natal Manthi point, the
                 Moon in the Badhaka (obstacle) sign, and the Moon-Saturn Punarpoo delay pattern being
                 activated right now. Any of these makes it a moment to avoid hasty commitments.
    notes        transit Mars crossing the question's house; transit Saturn over a relevant natal planet.
                 (Text only: Jupiter and Saturn are already weighed by the transit lens.)

The vote is +1 / 0 / -1 and comes only from the chart. The wording is plain and deterministic.
"""
from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Optional

_BAD_DIGNITY = ("debilitated", "enemy_sign")
_DUSTHANA = (6, 8, 12)

_CAUTION_EN = {
    "chandrashtama": "the Moon is 8th from your birth Moon",
    "manthi": "the Moon is over your Manthi point",
    "badhaka": "the Moon is in your obstacle sign",
    "punarpoo": "your Moon-Saturn delay pattern is active",
}
_CAUTION_LOCAL = {
    "hi_en": {
        "chandrashtama": "Chandra aapki janm rashi se 8th mein hai",
        "manthi": "Chandra aapke Manthi bindu par hai",
        "badhaka": "Chandra aapki badhak rashi mein hai",
        "punarpoo": "aapka Chandra-Shani deri ka pattern sakriya hai",
    },
    "te_en": {
        "chandrashtama": "Chandrudu mee janma rashi nundi 8va sthanamlo unnadu",
        "manthi": "Chandrudu mee Manthi bindu meeda unnadu",
        "badhaka": "Chandrudu mee badhaka rashilo unnadu",
        "punarpoo": "mee Chandra-Shani aalasya pattern sakriyamga undi",
    },
}


def _ord(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def build_naadi(pc: dict, cfg: dict, facts: dict, helpers: set[str], owned: dict[str, list[int]],
                primary: int) -> Optional[dict[str, Any]]:
    """The Chandra Naadi lens dict (with ``vote``), or None when the engine cannot run."""
    try:
        from chandra_naadi_analysis import (analyze_badhaka, analyze_chandrashtama, analyze_core_methodology,
                                            analyze_manthi_deep, analyze_punarpoo_deep, get_transit_positions)
        from goel_varga import house_from_lagna
    except Exception as exc:  # noqa: BLE001
        print(f"[question_naadi] unavailable: {type(exc).__name__}: {exc}", flush=True)
        return None
    # Same evaluation moment as the specialist bundle: today, noon.
    transit = get_transit_positions(datetime.combine(date.today(), time(12, 0)))
    if not transit or not (transit.get("Moon") or {}).get("sign"):
        return None
    planets = pc.get("planets") or {}
    lagna = str((pc.get("meta") or {}).get("lagna_sign") or "")
    try:
        _readings, touched = analyze_core_methodology(pc, transit)
        touched = list(dict.fromkeys(touched))
        cautions: list[str] = []
        if analyze_chandrashtama(pc, transit):
            cautions.append("chandrashtama")
        if any(r.rule_id == "V2_TRANSIT_MOON_OVER_MANTHI" for r in analyze_manthi_deep(pc, transit)):
            cautions.append("manthi")
        if any(r.severity == "caution" for r in analyze_badhaka(pc, transit)):
            cautions.append("badhaka")
        if any(r.severity == "caution" for r in analyze_punarpoo_deep(pc, transit)):
            cautions.append("punarpoo")
    except Exception as exc:  # noqa: BLE001
        print(f"[question_naadi] reading failed: {type(exc).__name__}: {exc}", flush=True)
        return None

    # Who carries THIS question: indicators, the house ruler, the question's houses and their rulers.
    carries = set(helpers) | set(cfg.get("karakas") or [])
    carries |= {pl for pl, d in planets.items() if int(d.get("house") or 0) == primary}
    supporting = {int(h) for h in cfg.get("supporting_houses") or []}
    carries |= {pl for pl, hs in owned.items() if supporting & set(hs)}
    relevant = [t for t in touched if t in carries]

    def strained(pl: str) -> bool:
        d = planets.get(pl) or {}
        return (int(d.get("house") or 0) in _DUSTHANA or str(d.get("dignity") or "") in _BAD_DIGNITY
                or bool(d.get("combust")))

    bad = [t for t in relevant if strained(t)]
    good = [t for t in relevant if t not in bad]
    vote = len(good) - len(bad) - (1 if cautions else 0)
    vote = 1 if vote > 0 else -1 if vote < 0 else 0

    mars_in = bool(lagna and (transit.get("Mars") or {}).get("sign")
                   and house_from_lagna(transit["Mars"]["sign"], lagna) == primary)
    sat_sign = (transit.get("Saturn") or {}).get("sign")
    sat_over = [pl for pl, d in planets.items() if sat_sign and d.get("sign") == sat_sign and pl in carries
                and pl != "Saturn"]
    return {"vote": vote, "touched": touched, "relevant": relevant, "good": good, "bad": bad,
            "moon_sign": transit["Moon"]["sign"], "cautions": cautions, "mars_in": mars_in,
            "sat_over": sat_over[:2], "primary": primary}


# --------------------------------------------------------------------------- wording
def text_en(d: dict, facts: dict) -> str:
    names = ", ".join(d["touched"])
    if not d["touched"]:
        first = "Chandra Naadi: the Moon is not touching any natal planet right now, so it adds no push either way."
    elif not d["relevant"]:
        who = "which does not carry" if len(d["touched"]) == 1 else "none of which carries"
        first = (f"Chandra Naadi: the Moon is now touching your natal {names}, {who} this "
                 f"question, so it neither pushes nor blocks it.")
    else:
        if d["good"] and d["bad"]:
            tail = f"{', '.join(d['good'])} helps while {', '.join(d['bad'])} is under strain"
        elif d["bad"]:
            tail = f"{', '.join(d['bad'])} carries this question but is under strain, so this moment brings pressure"
        else:
            tail = (f"{', '.join(d['good'])} carries this question and is well placed, so this is an active, "
                    f"helpful moment")
        first = f"Chandra Naadi: the Moon is now touching your natal {names}; {tail}."
    parts = [first]
    if d.get("cautions"):
        why = "; ".join(_CAUTION_EN[c] for c in d["cautions"][:2])
        end = "so go easy" if facts.get("domain_key") == "health_vitality" else "so avoid hasty commitments"
        parts.append(f"It is also a sensitive moment ({why}), {end}.")
    if d.get("sat_over"):                 # one transit note only: the more specific one
        parts.append(f"Transit Saturn is over your natal {' and '.join(d['sat_over'])}, which tests it.")
    elif d.get("mars_in"):
        parts.append(f"Transit Mars is in your {_ord(int(d['primary']))} house, which pushes this to a head.")
    return " ".join(parts)


def text_local(d: dict, facts: dict, lk: str) -> str:
    hi = lk == "hi_en"
    names = ", ".join(d["touched"])
    if not d["touched"]:
        first = ("Chandra Naadi: Chandra abhi kisi natal grah ko nahi chhu raha, isliye koi dhakka ya rukawat nahi." if hi else
                 "Chandra Naadi: Chandrudu ippudu e natal grahanni thakadam ledu, kabatti e vaipu prabhavam ledu.")
    elif not d["relevant"]:
        one = len(d["touched"]) == 1
        first = ((f"Chandra Naadi: Chandra abhi aapke natal {names} ko chhu raha hai, "
                  + ("jo is sawal ko nahi chalata" if one else "jinme se koi is sawal ko nahi chalata")
                  + ", isliye na dhakka na rukawat.") if hi
                 else (f"Chandra Naadi: Chandrudu ippudu mee natal {names} ni thakutunnadu, "
                       + ("adi ee prashnanu nadipinchadu" if one else "vaatilo e okkati ee prashnanu nadipinchadu")
                       + ", kabatti dhakka leda aapu ledu."))
    else:
        if d["good"] and d["bad"]:
            tail = (f"{', '.join(d['good'])} madad karta hai jabki {', '.join(d['bad'])} dabav mein hai" if hi else
                    f"{', '.join(d['good'])} maddatu istundi, {', '.join(d['bad'])} ibbandilo undi")
        elif d["bad"]:
            tail = (f"{', '.join(d['bad'])} is sawal ko chalata hai par dabav mein hai, isliye yeh samay dabav laata hai" if hi else
                    f"{', '.join(d['bad'])} ee prashnanu nadipistundi kani ibbandilo undi, kabatti ee samayam ottidi techchi pedutundi")
        else:
            tail = (f"{', '.join(d['good'])} is sawal ko chalata hai aur achhi sthiti mein hai, isliye yeh sakriya aur madadgaar samay hai" if hi else
                    f"{', '.join(d['good'])} ee prashnanu nadipistundi mariyu manchi sthitilo undi, kabatti idi chaitanyavantamaina, upayogakaramaina samayam")
        first = (f"Chandra Naadi: Chandra abhi aapke natal {names} ko chhu raha hai; {tail}." if hi else
                 f"Chandra Naadi: Chandrudu ippudu mee natal {names} ni thakutunnadu; {tail}.")
    parts = [first]
    if d.get("cautions"):
        why = "; ".join(_CAUTION_LOCAL[lk][c] for c in d["cautions"][:2])
        health = facts.get("domain_key") == "health_vitality"
        if hi:
            parts.append(f"Yeh ek sanvedansheel samay bhi hai ({why}), isliye "
                         + ("halka rahein." if health else "jaldbaazi mein koi vachan na dein."))
        else:
            parts.append(f"Idi oka sunnitamaina samayam kuda ({why}), kabatti "
                         + ("sunnitamga undandi." if health else "tondarapaatu nirnayalu teesukokandi."))
    n = _ord(int(d["primary"]))
    if d.get("sat_over"):                 # same single note as English
        sn = " aur ".join(d["sat_over"]) if hi else " mariyu ".join(d["sat_over"])
        parts.append(f"Gochar Shani aapke natal {sn} par hai, jo ise parakhta hai." if hi else
                     f"Gochara Shani mee natal {sn} meeda unnadu, idi deenini pareekshistundi.")
    elif d.get("mars_in"):
        parts.append(f"Gochar Mangal aapke {n} house mein hai, jo ise charam par le jata hai." if hi else
                     f"Gochara Mangaludu mee {n} house lo unnadu, idi daanini charama sthayiki teesukuvastundi.")
    return " ".join(parts)
