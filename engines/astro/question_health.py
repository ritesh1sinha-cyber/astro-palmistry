"""Body vulnerability for a health question: where this chart is sensitive, and whether it is a bad time.

Two independent readings are folded into one lens:

    disease pattern   V.P. Goel's method (goel_disease_analysis + goel_disease_confluence): the
                      D27 / D3 / D6 / nakshatra layers agree on a body zone, only when >= 70% of the
                      relevant layers agree.
    Chandra Naadi     planets standing in the 6th and 8th houses (analyze_health), and Chandrashtama
                      (the transiting Moon in the 8th from the birth Moon).

Everything is deterministic and in plain words. It never names an illness, never estimates a lifespan,
and the wording is written to survive the customer-text sanitizer (see ``sanitized``): that filter
deletes a whole sentence when it holds two organ names in a list, so organs are described by function.
"""
from __future__ import annotations

import re
from typing import Any, Optional

# --------------------------------------------------------------------------- plain wording
_THEME_LABEL = {
    "face_eyes_oral": "the face, eyes, mouth and head",
    "blood_pressure_heart": "blood pressure and circulation",
    "ent_lungs_breath": "breathing and the throat",
    "bowel_gut": "digestion and the bowels",
    "urinary_reproductive": "the urinary and pelvic area",
}
_CHRONIC = "chronic_hidden"

_AREAS = {
    "Sun": "eyes and vitality",
    "Moon": "sleep and stress",
    "Mars": "blood pressure and inflammation",
    "Mercury": "skin and nerves",
    "Jupiter": "digestion and sugar balance",
    "Venus": "hormones and skin",
    "Saturn": "joints and teeth",
    "Rahu": "allergies and restlessness",
    "Ketu": "hard-to-pin-down complaints",
}

# Hinglish / Tenglish (Roman script). Kept here so the English and local wording cannot drift apart.
LOCAL = {
    "hi_en": {
        "themes": {
            "face_eyes_oral": "chehra, aankhein, munh aur sir",
            "blood_pressure_heart": "blood pressure aur circulation",
            "ent_lungs_breath": "saans aur gala",
            "bowel_gut": "pachan aur pet",
            "urinary_reproductive": "mutra aur pelvic hissa",
        },
        "areas": {
            "Sun": "aankhein aur taakat",
            "Moon": "neend aur tanav",
            "Mars": "blood pressure aur sujan",
            "Mercury": "tvacha aur naadiyan",
            "Jupiter": "pachan aur sugar santulan",
            "Venus": "hormone aur tvacha",
            "Saturn": "jodon aur daanton",
            "Rahu": "allergy aur bechaini",
            "Ketu": "pakad mein na aane wali takleefein",
        },
        "chronic": "dheere badhne wala tanav jise nazarandaz karna aasaan hai",
        "and": " aur ",
    },
    "te_en": {
        "themes": {
            "face_eyes_oral": "mukham, kallu, noru mariyu thala",
            "blood_pressure_heart": "blood pressure mariyu circulation",
            "ent_lungs_breath": "shwasa mariyu gontu",
            "bowel_gut": "jeernakriya mariyu kadupu",
            "urinary_reproductive": "mutra mariyu pelvic bhagam",
        },
        "areas": {
            "Sun": "kallu mariyu shakti",
            "Moon": "nidra mariyu ottidi",
            "Mars": "blood pressure mariyu vaapu",
            "Mercury": "charmam mariyu narallu",
            "Jupiter": "jeernam mariyu sugar samatulyata",
            "Venus": "hormonelu mariyu charmam",
            "Saturn": "keellu mariyu pallu",
            "Rahu": "allergylu mariyu atirikta chanchalyam",
            "Ketu": "gurtinchaleni ibbandulu",
        },
        "chronic": "mellaga perige ottidi, daanini nirlakshyam cheyadam sulabham",
        "and": " mariyu ",
    },
}

_PREVENT = {
    "face_eyes_oral": "have your eyes and teeth checked and take regular screen breaks",
    "blood_pressure_heart": "check your blood pressure once a year and walk daily",
    "ent_lungs_breath": "keep away from smoke and dust and treat colds early",
    "bowel_gut": "eat at fixed times and prefer warm cooked food when stressed",
    "urinary_reproductive": "stay well hydrated and do not ignore a recurring discomfort",
    _CHRONIC: "keep a steady routine and a yearly full check-up",
}
_PREVENT_LOCAL = {
    "hi_en": {
        "face_eyes_oral": "aankhein aur daant check karwayein aur screen se break lete rahein",
        "blood_pressure_heart": "saal mein ek baar blood pressure check karwayein aur roz paidal chalein",
        "ent_lungs_breath": "dhuen aur dhool se bachein aur sardi-zukham ka jaldi ilaaj karein",
        "bowel_gut": "tay samay par khayein aur tanav mein garam pakka khana lein",
        "urinary_reproductive": "khoob paani piyein aur baar baar hone wali takleef ko nazarandaz na karein",
        _CHRONIC: "ek niyamit dinacharya rakhein aur saal mein ek baar poora check-up karwayein",
    },
    "te_en": {
        "face_eyes_oral": "kallu mariyu pallu pareekshinchukondi, screen nundi viraamam teesukondi",
        "blood_pressure_heart": "samvatsaraniki oka sari blood pressure choosukondi, roju nadavandi",
        "ent_lungs_breath": "pogaa mariyu dhooli nundi dooramga undandi, jalubunu mundugaa chikitsa cheyandi",
        "bowel_gut": "nirnita samayamlo bhojanam cheyandi, ottidilo vechati vandina aaharam teesukondi",
        "urinary_reproductive": "ekkuva neellu taagandi, marumaru vache ibbandini nirlakshyam cheyakandi",
        _CHRONIC: "kramabaddhamaina dinacharya patinchandi, samvatsaraniki oka sari poorti check-up cheyinchukondi",
    },
}

_SIGNS = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius",
          "Capricorn", "Aquarius", "Pisces")


def _ord(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _and(items: list[str], lk: str = "en") -> str:
    word = " and " if lk == "en" else LOCAL[lk]["and"]
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + word + items[-1]


def _zones(zones: list[str], lk: str = "en") -> str:
    """Zone labels already contain "and", so two of them are joined with a clearer connector."""
    glue = {"en": ", as well as ", "hi_en": ", saath hi ", "te_en": ", alaage "}[lk]
    return glue.join(zones)


def sanitized(text: str) -> bool:
    """True when the customer-text sanitizer would leave this sentence alone."""
    try:
        from qa_checks.customer_text_sanitizer import _internal_leak
        return not _internal_leak(text)
    except Exception:  # noqa: BLE001
        return True


# --------------------------------------------------------------------------- the readings
def _goel(pc: dict) -> dict[str, Any]:
    try:
        from goel_disease_analysis import analyze_disease_chart
        from goel_disease_confluence import build_health_confluence
        analysis = analyze_disease_chart(pc)
        if analysis.get("error"):
            return {}
        conf = build_health_confluence(analysis, pc)
    except Exception as exc:  # noqa: BLE001
        print(f"[question_health] disease pattern unavailable: {type(exc).__name__}: {exc}", flush=True)
        return {}
    themes = [{"id": p["theme_id"], "pct": int(p.get("match_pct") or 0)} for p in conf.get("predictions", [])]
    now_row = next((r for r in analysis.get("active_health_periods", [])
                    if r.get("level") == "antardasha" and r.get("status") == "current"), None)
    upcoming = (analysis.get("upcoming_health_windows") or [{}])[0]
    watch = ({"lord": upcoming.get("lord", ""), "range": upcoming.get("range", "")}
             if upcoming.get("lord") else None)
    now = ({"lord": now_row.get("lord", ""), "range": now_row.get("range", "")} if now_row else None)
    return {"themes": themes, "current_hard": bool(now_row), "watch": watch, "now": now}


def _naadi(pc: dict, moon_transit_sign: str) -> dict[str, Any]:
    sensitive: list[dict] = []
    try:
        from chandra_naadi_analysis import analyze_health
        for r in analyze_health(pc):
            planet = (getattr(r, "planets_involved", None) or [""])[0]
            house = (getattr(r, "houses_involved", None) or [0])[0]
            if planet in _AREAS and house and not any(s["planet"] == planet for s in sensitive):
                sensitive.append({"planet": planet, "house": int(house)})
    except Exception as exc:  # noqa: BLE001
        print(f"[question_health] Chandra Naadi health unavailable: {type(exc).__name__}: {exc}", flush=True)
    sensitive.sort(key=lambda s: (s["house"], s["planet"]))      # the 6th (illness) before the 8th
    natal_moon = str(((pc.get("planets") or {}).get("Moon") or {}).get("sign") or "")
    chandrashtama = False
    if natal_moon in _SIGNS and moon_transit_sign in _SIGNS:
        chandrashtama = (_SIGNS.index(moon_transit_sign) - _SIGNS.index(natal_moon)) % 12 + 1 == 8
    return {"sensitive": sensitive, "chandrashtama": chandrashtama}


def build_vulnerability(pc: dict, conf: Any) -> Optional[dict[str, Any]]:
    """The lens dict (with ``vote``) for a health question, or None when neither reading is available."""
    moon = re.search(r"Transit Moon in (\w+)", getattr(conf, "transit_finding", "") or "")
    g = _goel(pc)
    n = _naadi(pc, moon.group(1) if moon else "")
    themes = g.get("themes", [])
    if not themes and not n["sensitive"] and not n["chandrashtama"]:
        return None
    pts = (min(len([t for t in themes if t["id"] != _CHRONIC]), 2) + min(len(n["sensitive"]), 2)
           + (1 if n["chandrashtama"] else 0) + (1 if g.get("current_hard") else 0)
           + (1 if any(t["id"] == _CHRONIC for t in themes) else 0))
    vote = -1 if pts >= 4 else 1 if pts <= 1 else 0
    return {"vote": vote, "themes": themes[:4], "sensitive": n["sensitive"][:2],
            "chandrashtama": n["chandrashtama"], "current_hard": bool(g.get("current_hard")),
            "watch": g.get("watch"), "now": g.get("now")}


# --------------------------------------------------------------------------- wording
def zone_labels(d: dict, lk: str = "en") -> list[str]:
    ids = [t["id"] for t in d.get("themes", []) if t["id"] in _THEME_LABEL][:2]
    table = _THEME_LABEL if lk == "en" else LOCAL[lk]["themes"]
    return [table[i] for i in ids]


def has_chronic(d: dict) -> bool:
    return any(t["id"] == _CHRONIC for t in d.get("themes", []))


def text_en(d: dict) -> str:
    zones = zone_labels(d)
    parts: list[str] = []
    if zones or has_chronic(d):
        s = "Your chart's body pattern shows " + (
            f"{_zones(zones)} as the places where stress shows first" if zones else "slow-building strain")
        if zones and has_chronic(d):
            s += ", plus slow-building strain"
        parts.append(s + ".")
    if d.get("sensitive"):
        bits = [f"{s['planet']} in your {_ord(s['house'])} house ({_AREAS[s['planet']]})" for s in d["sensitive"]]
        parts.append(f"Chandra Naadi marks {_and(bits)} as sensitive.")
    # (Chandrashtama is said once, in the Chandra Naadi reason; it still counts towards the lens vote.)
    if not parts:
        parts.append("Your chart shows no marked body sensitivity.")
    text = " ".join(parts)
    # Anything the sanitizer would swallow is dropped from the end, never allowed to blank the bullet.
    while not sanitized(text) and len(parts) > 1:
        parts.pop()
        text = " ".join(parts)
    return text if sanitized(text) else "Your chart shows a few body areas that need steady care."


def text_local(d: dict, lk: str) -> str:
    hi = lk == "hi_en"
    L = LOCAL[lk]
    zones = zone_labels(d, lk)
    parts: list[str] = []
    if zones or has_chronic(d):
        if zones:
            s = (f"Aapki kundli ka sharir-pattern dikhata hai ki tanav sabse pehle {_zones(zones, lk)} mein dikhta hai"
                 if hi else f"Mee jatakam sharira-pattern prakaaram ottidi modata {_zones(zones, lk)} lo kanipistundi")
            if has_chronic(d):
                s += (f", saath hi {L['chronic']}" if hi else f", alaage {L['chronic']}")
        else:
            s = (f"Aapki kundli {L['chronic']} dikhati hai" if hi else f"Mee jatakam {L['chronic']} choopistundi")
        parts.append(s + ".")
    if d.get("sensitive"):
        bits = [(f"{s['planet']} aapke {_ord(s['house'])} house mein ({L['areas'][s['planet']]})" if hi
                 else f"{s['planet']} mee {_ord(s['house'])} house lo ({L['areas'][s['planet']]})")
                for s in d["sensitive"]]
        parts.append((f"Chandra Naadi {_and(bits, lk)} ko sanvedansheel maanti hai." if hi
                      else f"Chandra Naadi {_and(bits, lk)} ni sunnitamga choosthundi."))
    if not parts:
        parts.append("Aapki kundli mein koi khaas sharirik sanvedansheelta nahi dikhti." if hi
                     else "Mee jatakam lo pratyekamaina sharira sunnitatvam kanipinchadam ledu.")
    text = " ".join(parts)
    while not sanitized(text) and len(parts) > 1:
        parts.pop()
        text = " ".join(parts)
    return text


def answer_line(d: dict, lk: str = "en") -> str:
    """One sentence for the headline answer: which places to look after."""
    zones = zone_labels(d, lk)
    if lk == "en":
        if zones:
            return f"Look after {_zones(zones)}; those are where your chart is most sensitive."
        if d.get("sensitive"):
            return f"Look after your {_AREAS[d['sensitive'][0]['planet']].split(',')[0]}; your chart is sensitive there."
        return ""
    hi = lk == "hi_en"
    if zones:
        return (f"{_zones(zones, lk)} ka dhyan rakhein; kundli mein yahi sabse sanvedansheel hain." if hi
                else f"{_zones(zones, lk)} vishayamlo jagrattha teesukondi; jatakam lo ivi atyanta sunnitamainavi.")
    return ""


def prevent_step(d: dict, lk: str = "en") -> str:
    """The one preventive habit that matches the strongest body zone (or the slow-strain pattern)."""
    ids = [t["id"] for t in d.get("themes", []) if t["id"] in _THEME_LABEL]
    key = ids[0] if ids else (_CHRONIC if has_chronic(d) else "")
    if not key:
        return ""
    if lk == "en":
        return f"For your body pattern, {_PREVENT[key]}."
    hi = lk == "hi_en"
    return (f"Aapke sharir-pattern ke liye: {_PREVENT_LOCAL[lk][key]}." if hi
            else f"Mee sharira-pattern kosam: {_PREVENT_LOCAL[lk][key]}.")


def watch_line(d: dict, lk: str = "en") -> str:
    """When to take more care: the sensitive sub-period running now (if any) and the next one."""
    w, now = d.get("watch"), d.get("now")
    w = w if w and w.get("range") else None
    now = now if now and now.get("range") else None
    if not w and not now:
        return ""
    hi = lk == "hi_en"
    if lk == "en":
        if now and w:
            return (f"The {now['lord']} sub-period you are in ({now['range']}) already asks for care; the next "
                    f"sensitive stretch is the {w['lord']} sub-period ({w['range']}).")
        if now:
            return f"The {now['lord']} sub-period you are in ({now['range']}) asks for extra care."
        return f"Take most care of your health around {w['range']}, the {w['lord']} sub-period."
    if now and w:
        return (f"Abhi chal rahi {now['lord']} antardasha ({now['range']}) mein hi dhyan rakhna zaroori hai; agla "
                f"sanvedansheel daur {w['lord']} antardasha ({w['range']}) hai." if hi else
                f"Ippudu nadustunna {now['lord']} antardasha ({now['range']}) lone jagrattha avasaram; tarvati "
                f"sunnitamaina daur {w['lord']} antardasha ({w['range']}).")
    if now:
        return (f"Abhi chal rahi {now['lord']} antardasha ({now['range']}) mein extra dhyan rakhein." if hi else
                f"Ippudu nadustunna {now['lord']} antardasha ({now['range']}) lo ekkuva jagrattha teesukondi.")
    return (f"Sehat ka sabse zyada dhyan {w['range']} ke aaspaas rakhein, jab {w['lord']} antardasha hogi." if hi
            else f"{w['range']} chuttu aarogyam vishayamlo ekkuva jagrattha teesukondi, appudu {w['lord']} antardasha untundi.")
