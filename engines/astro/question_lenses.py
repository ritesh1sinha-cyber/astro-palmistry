"""The six lenses a question is judged through, each reduced to one vote.

    promise      the birth chart itself: the house lord, the natural indicator, the sign score
    vimshottari  the main/sub period you are in, and how that planet relates to the question
    jaimini      the Chara dasha signs and whether they light up the question's house sign
    yogini       the running Yogini period and its tone
    transit      Jupiter and Saturn (and the nodes) against the question's house
    naadi        Chandra Naadi: which natal planets the transiting Moon is touching right now

Every vote is +1 (supports), 0 (neutral) or -1 (strains), worked out from the chart with
fixed rules, never by the model. ``score`` weights the birth promise double against the
five live lenses, so a weak promise cannot be waved away by one friendly transit.
"""
from __future__ import annotations

import re
from typing import Any

SIGNS = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius",
         "Capricorn", "Aquarius", "Pisces")
_SIGN_LORD = {"Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon", "Leo": "Sun",
              "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars", "Sagittarius": "Jupiter",
              "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter"}
_BAD_DIGNITY = ("debilitated", "enemy_sign")
_DUSTHANA = (6, 8, 12)

LENS_ORDER = ("promise", "vimshottari", "jaimini", "yogini", "transit", "naadi")


def _idx(sign: str) -> int:
    try:
        return SIGNS.index(str(sign).strip().title())
    except ValueError:
        return -1


def owned_houses(lagna: str) -> dict[str, list[int]]:
    li = _idx(lagna)
    out: dict[str, list[int]] = {}
    if li < 0:
        return out
    for i, s in enumerate(SIGNS):
        out.setdefault(_SIGN_LORD[s], []).append((i - li) % 12 + 1)
    return out


def rashi_drishti(sign: str) -> set[str]:
    """Jaimini sign aspects: movable -> fixed (not the next), fixed -> movable (not the previous),
    dual -> the other duals. A sign always counts as 'lighting up' itself."""
    i = _idx(sign)
    if i < 0:
        return set()
    movable, fixed, dual = {0, 3, 6, 9}, {1, 4, 7, 10}, {2, 5, 8, 11}
    seen = {i}
    if i in movable:
        seen |= {j for j in fixed if j != (i + 1) % 12}
    elif i in fixed:
        seen |= {j for j in movable if j != (i - 1) % 12}
    else:
        seen |= dual - {i}
    return {SIGNS[j] for j in seen}


def _position_from(target: str, base: str) -> int:
    t, b = _idx(target), _idx(base)
    return 0 if t < 0 or b < 0 else (t - b) % 12 + 1


def _clamp(n: int) -> int:
    return 1 if n > 0 else -1 if n < 0 else 0


def _relation(planet: str, helpers: set[str], pc: dict, owned: dict[str, list[int]], primary_house: int) -> str:
    """helper / hard / none: how a running planet stands to this question."""
    if not planet:
        return "none"
    house = int(((pc.get("planets") or {}).get(planet) or {}).get("house") or 0)
    if planet in helpers or house == primary_house:
        return "helper"
    mine = owned.get(planet, [])
    if house in _DUSTHANA or (mine and all(h in _DUSTHANA for h in mine)):
        return "hard"
    return "none"


def build_lenses(conf: Any, pc: dict, cfg: dict, facts: dict) -> dict[str, dict]:
    """``facts`` must already hold house/karakas/periods/transit_parts/signals (see build_fact_sheet)."""
    out: dict[str, dict] = {}
    h = facts["house"]
    lord = h["lord"]
    primary = int(h["number"])
    owned = owned_houses(facts["lagna"])
    helpers = {lord["planet"], facts["lagna_lord"], *[k["planet"] for k in facts["karakas"]]}

    # ---- birth promise: the static signals only (the running period has its own lens)
    n_for, n_against = len(facts["signals_for"]), len(facts["signals_against"])
    out["promise"] = {"vote": 1 if n_for - n_against >= 2 else -1 if n_against - n_for >= 2 else 0}

    # ---- Vimshottari
    p = facts["periods"]
    if p.get("sub"):
        rel_sub = _relation(p["sub"], helpers, pc, owned, primary)
        rel_main = _relation(p["main"], helpers, pc, owned, primary)
        who, rel = (p["sub"], rel_sub) if rel_sub != "none" else (p["main"], rel_main) if rel_main != "none" \
            else (p["sub"], "none")
        out["vimshottari"] = {"vote": {"helper": 1, "hard": -1, "none": 0}[rel], "main": p["main"],
                              "sub": p["sub"], "who": who, "rel": rel}

    # ---- Jaimini Chara dasha
    chara = ((pc.get("jaimini") or {}).get("chara_dasha") or {})
    maha = str((chara.get("current_maha") or {}).get("sign") or "")
    antar = str((chara.get("current_antar") or {}).get("sign") or "")
    if _idx(maha) >= 0 and _idx(antar) >= 0 and _idx(h["sign"]) >= 0:
        lit = rashi_drishti(maha) | rashi_drishti(antar)
        hit = "primary" if h["sign"] in lit else "lord" if lord["sign"] in lit else ""
        hard = (not hit) and _position_from(h["sign"], antar) in _DUSTHANA
        out["jaimini"] = {"vote": 1 if hit else -1 if hard else 0, "maha": maha, "antar": antar,
                          "hit": hit, "hard": hard, "primary_sign": h["sign"], "lord_sign": lord["sign"]}

    # ---- Yogini
    yog = (pc.get("yogini") or {})
    cur = yog.get("current_yogini") or {}
    if cur.get("yogini"):
        tone = str(cur.get("tone") or "")
        if not tone:
            row = next((r for r in (yog.get("full_cycle") or []) if r.get("status") == "current"), {})
            tone = str(row.get("tone") or "")
        tone = tone if tone in ("auspicious", "inauspicious") else "mixed"
        tie = str(cur.get("lord") or "") in helpers
        vote = 1 if tone == "auspicious" else 0 if (tone == "inauspicious" and tie) or tone == "mixed" else -1
        out["yogini"] = {"vote": vote, "name": cur["yogini"], "lord": cur.get("lord") or "",
                         "tone": tone, "tie": tie}

    # ---- transit (Jupiter, Saturn, the nodes)
    parts = {pl: (int(hh), sg) for pl, hh, sg in facts.get("transit_parts") or []}
    if parts:
        def mode(planet: str, offsets: tuple[int, ...]) -> tuple[str, int]:
            if planet not in parts:
                return "", 0
            th = parts[planet][0]
            if th == primary:
                return "in", th
            return ("aspects" if ((primary - th) % 12) + 1 in offsets else "none"), th

        jm, jh = mode("Jupiter", (5, 7, 9))
        sm, sh = mode("Saturn", (3, 7, 10))
        ax = re.search(r"Rahu-Ketu Axis in Houses (\d+)/(\d+)", conf.transit_finding or "")
        nodes = bool(ax) and primary in (int(ax.group(1)), int(ax.group(2)))
        score = (1 if jm in ("in", "aspects") else 0) - (1 if sm in ("in", "aspects") else 0) - (1 if nodes else 0)
        out["transit"] = {"vote": _clamp(score), "jup": {"mode": jm, "house": jh},
                          "sat": {"mode": sm, "house": sh}, "nodes": nodes, "primary": primary}

    # ---- Chandra Naadi: the transiting Moon's live contacts with natal planets
    cn = ((getattr(conf, "specialist_readings", None) or {}).get("chandra_naadi") or {})
    if cn.get("status") == "available":
        touched = []
        for f in cn.get("findings") or []:
            m = re.match(r"Transit Moon Activates Natal (\w+)", str((f or {}).get("title") or ""))
            if m and m.group(1) not in touched:
                touched.append(m.group(1))
        in_primary = {pl for pl, d in (pc.get("planets") or {}).items() if int(d.get("house") or 0) == primary}
        carries = helpers | in_primary
        relevant = [t for t in touched if t in carries]

        def strained(pl: str) -> bool:
            d = (pc.get("planets") or {}).get(pl) or {}
            return (int(d.get("house") or 0) in _DUSTHANA or str(d.get("dignity") or "") in _BAD_DIGNITY
                    or bool(d.get("combust")))

        bad = [t for t in relevant if strained(t)]
        good = [t for t in relevant if t not in bad]
        moon = re.search(r"Transit Moon in (\w+)", conf.transit_finding or "")
        out["naadi"] = {"vote": _clamp(len(good) - len(bad)), "touched": touched, "relevant": relevant,
                        "good": good, "bad": bad, "moon_sign": moon.group(1) if moon else ""}
    return out


def score(lenses: dict[str, dict]) -> int:
    live = sum(v["vote"] for k, v in lenses.items() if k != "promise")
    return 2 * lenses.get("promise", {}).get("vote", 0) + live


def stance(lenses: dict[str, dict]) -> str:
    s = score(lenses)
    return "favourable" if s >= 3 else "difficult" if s <= -3 else "mixed"


def promise_and_now(lenses: dict[str, dict]) -> tuple[int, int]:
    """(birth promise vote, live verdict) where the live verdict needs a clear lean of two lenses."""
    live = sum(v["vote"] for k, v in lenses.items() if k != "promise")
    return lenses.get("promise", {}).get("vote", 0), (1 if live >= 2 else -1 if live <= -2 else 0)


def confidence(lenses: dict[str, dict]) -> str:
    s = abs(score(lenses))
    return "high" if s >= 5 else "moderate" if s >= 3 else "low"


# ----------------------------------------------------------------------------- English wording
def _ord(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def text_en(key: str, d: dict, facts: dict) -> str:
    n = _ord(int(facts["house"]["number"]))
    if key == "vimshottari":
        base = f"You are running the {d['main']} main period and {d['sub']} sub-period."
        who = d["who"]
        tail = {"helper": f" {who} carries this question, so the period backs it.",
                "hard": f" {who} sits in or rules a hard house, so the period brings delay.",
                "none": f" {who} has no direct link to this question, so it neither pushes nor blocks."}
        return base + tail[d["rel"]]
    if key == "jaimini":
        head = f"Your Chara period ({d['maha']} main, {d['antar']} sub)"
        if d["hit"] == "primary":
            return f"{head} lights up your {n} house sign ({d['primary_sign']}), which helps."
        if d["hit"] == "lord":
            return f"{head} lights up {d['lord_sign']}, where your {n} house ruler sits, which helps."
        if d["hard"]:
            return (f"{head} does not reach your {n} house sign ({d['primary_sign']}) and sits awkwardly "
                    f"to it, so progress is slower.")
        return f"{head} neither lights up nor blocks your {n} house sign ({d['primary_sign']})."
    if key == "yogini":
        head = f"Yogini: you are in the {d['name']} ({d['lord']}) period"
        if d["tone"] == "auspicious":
            return head + ", a favourable one" + (
                f", and {d['lord']} also carries this question, which adds to it." if d["tie"] else ".")
        if d["tone"] == "inauspicious":
            return head + ", a testing one" + (
                f", though {d['lord']} also carries this question, which softens it." if d["tie"] else ".")
        return head + ", a mixed one."
    if key == "transit":
        p = d["primary"]
        jup = {"in": f"Jupiter is crossing your {_ord(p)} house itself, which blesses it",
               "aspects": f"Jupiter, crossing your {_ord(d['jup']['house'])} house, looks at your {_ord(p)} "
                          f"house and supports it",
               "none": f"Jupiter, crossing your {_ord(d['jup']['house'])} house, is not touching your "
                       f"{_ord(p)} house"}.get(d["jup"]["mode"], "")
        sat = {"in": f"Saturn is crossing your {_ord(p)} house itself, which slows and tests it",
               "aspects": f"Saturn, crossing your {_ord(d['sat']['house'])} house, looks at your {_ord(p)} "
                          f"house and adds pressure",
               "none": f"Saturn, crossing your {_ord(d['sat']['house'])} house, is not pressing your "
                       f"{_ord(p)} house"}.get(d["sat"]["mode"], "")
        text = "Transits: " + "; ".join(x for x in (jup, sat) if x) + "."
        if d["nodes"]:
            text += f" Rahu and Ketu sit across your {_ord(p)} house axis, which unsettles it."
        return text
    if key == "naadi":
        if not d["touched"]:
            return "Chandra Naadi: the Moon is not touching any natal planet right now, so it adds no push either way."
        names = ", ".join(d["touched"])
        if not d["relevant"]:
            return (f"Chandra Naadi: the Moon is now touching your natal {names}, none of which carries this "
                    f"question, so it neither pushes nor blocks it.")
        if d["good"] and d["bad"]:
            tail = f"{', '.join(d['good'])} helps while {', '.join(d['bad'])} is under strain"
        elif d["bad"]:
            tail = f"{', '.join(d['bad'])} carries this question but is under strain, so this moment brings pressure"
        else:
            tail = f"{', '.join(d['good'])} carries this question and is well placed, so this is an active, " \
                   f"helpful moment"
        return f"Chandra Naadi: the Moon is now touching your natal {names}; {tail}."
    return ""

