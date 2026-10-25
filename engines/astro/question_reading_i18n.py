"""Hinglish (hi_en) and Tenglish (te_en) wording for ``question_reading``.

A 7B model cannot translate astrology sentences reliably (it turned "your marriage will
face delays" into nonsense), so every non-English line is built from fixed templates over
the same fact sheet. The model still decides the verdict and which findings matter; only
the wording of the lines it picks from is localised here.
"""
from __future__ import annotations

import re
from typing import Any

import question_reading as QR

_DAY = {
    "hi_en": {"Sunday": "Ravivaar", "Monday": "Somvaar", "Tuesday": "Mangalvaar", "Wednesday": "Budhvaar",
              "Thursday": "Guruvaar", "Friday": "Shukravaar", "Saturday": "Shanivaar"},
    "te_en": {"Sunday": "Aadivaaram", "Monday": "Somavaaram", "Tuesday": "Mangalavaaram",
              "Wednesday": "Budhavaaram", "Thursday": "Guruvaaram", "Friday": "Shukravaaram",
              "Saturday": "Shanivaaram"},
}
_AND = {"hi_en": " aur ", "te_en": " mariyu "}

# dignity -> clause that continues "... sits in house N in <Sign>"
_DIGNITY = {
    "hi_en": {"exalted": " aur uchch ka (sabse majboot) hai", "own_sign": " aur apni rashi mein (majboot) hai",
              "moolatrikona": " aur apni rashi mein (majboot) hai", "friendly_sign": " aur mitra rashi mein hai",
              "debilitated": " aur neech ka (kamzor) hai", "enemy_sign": " aur shatru rashi mein hai"},
    "te_en": {"exalted": " mariyu uchchalo (chala balanga) undi", "own_sign": " mariyu swa-rashilo (balanga) undi",
              "moolatrikona": " mariyu swa-rashilo (balanga) undi", "friendly_sign": " mariyu mitra rashilo undi",
              "debilitated": " mariyu neecha sthithilo (balaheenanga) undi",
              "enemy_sign": " mariyu shatru rashilo undi"},
}
_BITS = {
    "hi_en": {"hard": "kathin house mein", "weak": "kamzor", "combust": "Surya ke bahut paas"},
    "te_en": {"hard": "kashtamaina house lo", "weak": "balaheenanga", "combust": "Suryudiki chala daggara"},
}
_FINGER = {
    "hi_en": {"little": "chhoti", "ring": "anamika", "middle": "beech ki", "index": "tarjani",
              " or ": " ya ", "finger": "ungli"},
    "te_en": {"little": "chinna", "ring": "ungaram", "middle": "madhyama", "index": "choopudu",
              " or ": " leda ", "finger": "vrelu"},
}
_METAL = {
    "hi_en": {"gold": "sone", "silver": "chandi", "copper": "taambe", "brass": "peetal", "iron": "lohe",
              "platinum": "platinum", " or ": " ya ", "panchdhatu": "panchdhatu"},
    "te_en": {"gold": "bangaram", "silver": "vendi", "copper": "raagi", "brass": "pitthala", "iron": "inumu",
              "platinum": "platinum", " or ": " leda ", "panchdhatu": "panchdhatu"},
}
_AVOID_WHY = {
    "hi_en": {
        "it sits in your 8th house, which stirs up sudden trouble":
            "yeh aapke 8th house mein baitha hai, jo achanak pareshani laata hai",
        "it rules a difficult house (6th, 8th or 12th) and could magnify those problems":
            "yeh kathin house (6th, 8th ya 12th) ka swami hai aur un samasyaon ko badha sakta hai",
        "it rules a house of loss or obstruction for your rising sign":
            "yeh aapke lagna ke liye haani ya rukawat ke ghar ka swami hai",
        "it is not a safe stone for your chart": "yeh aapki kundli ke liye surakshit ratna nahi hai",
    },
    "te_en": {
        "it sits in your 8th house, which stirs up sudden trouble":
            "idi mee 8th house lo undi, appudappudu ibbandulu techchi pedutundi",
        "it rules a difficult house (6th, 8th or 12th) and could magnify those problems":
            "idi kashtamaina house (6th, 8th leda 12th) ki adhipati, aa samasyalanu penchavachchu",
        "it rules a house of loss or obstruction for your rising sign":
            "idi mee lagnaniki nashtam leda aatankam kaliginche house ki adhipati",
        "it is not a safe stone for your chart": "idi mee jatakaniki surakshitamaina ratnam kaadu",
    },
}


def _swap(text: str, table: dict[str, str]) -> str:
    out = str(text or "")
    for en, loc in table.items():
        out = re.sub(re.escape(en), loc, out, flags=re.I)
    return out


def _day(name: str, lk: str) -> str:
    return _DAY[lk].get(name, name)


def window(text: str, lk: str) -> str:
    """'Venus sub-period (Feb 2027 to Oct 2029)' in the reader's language."""
    out = str(text or "")
    if lk == "hi_en":
        out = out.replace("sub-period", "antardasha").replace("main period", "mahadasha")
        return re.sub(r"\((.+?) to (.+?)\)", r"(\1 se \2 tak)", out)
    out = out.replace("sub-period", "antardasha").replace("main period", "mahadasha")
    return re.sub(r"\((.+?) to (.+?)\)", r"(\1 nundi \2 varaku)", out)


def _dw(dig: str, lk: str) -> str:
    return _DIGNITY[lk].get(str(dig or ""), "")


def _state(k: dict, lk: str) -> str:
    bits = []
    if k["hard_house"]:
        bits.append(_BITS[lk]["hard"])
    if k["dignity"] in QR._BAD_DIGNITY:
        bits.append(_BITS[lk]["weak"])
    if k["combust"]:
        bits.append(_BITS[lk]["combust"])
    if lk == "hi_en":
        return f"dabav mein hai ({', '.join(bits)})" if bits else "achhi sthiti mein hai"
    return f"ibbandilo undi ({', '.join(bits)})" if bits else "manchi sthithilo undi"


def transits(facts: dict, lk: str) -> str:
    parts = facts.get("transit_parts") or []
    if not parts:
        return ""
    if lk == "hi_en":
        body = "; ".join(f"{p} aapke {QR._ord(int(h))} house ({s}) se guzar raha hai" for p, h, s in parts)
        return f"Abhi {body}."
    body = "; ".join(f"{p} mee {QR._ord(int(h))} house ({s}) gunda sancharistunnadu" for p, h, s in parts)
    return f"Ippudu {body}."


def findings(facts: dict, lk: str) -> list[tuple[str, str]]:
    if facts["domain_key"] in ("gemstones_remedies", "out_of_domain"):
        return []
    h = facts["house"]
    lord = h["lord"]
    hi = lk == "hi_en"
    dw = _dw(lord["dignity"], lk)
    if hi:
        f1 = (f"{lord['planet']} aapke {QR._ord(h['number'])} house ka swami hai, jo is sawal ko chalata hai. "
              f"Woh {lord['sign']} mein house {lord['house']} mein baitha hai{dw}."
              + (" Yeh kathin house hai, jo deri laata hai." if lord["hard_house"]
                 else " Yeh sahayak sthiti hai."))
    else:
        f1 = (f"{lord['planet']} mee {QR._ord(h['number'])} house ki adhipati, ee prashnanu nadipistundi. "
              f"Adi {lord['sign']} lo house {lord['house']} lo undi{dw}."
              + (" Idi kashtamaina house, aalasyam kaligistundi." if lord["hard_house"]
                 else " Idi anukulamaina sthiti."))
    rows = [("F1", f1)]
    for k in facts["karakas"]:
        if k["planet"] == lord["planet"]:
            continue
        if hi:
            t = (f"{k['planet']}, is vishay ka natural karak, house {k['house']} ({k['sign']}) mein hai "
                 f"aur {_state(k, lk)}.")
        else:
            t = (f"{k['planet']}, ee vishayaniki natural karakudu, house {k['house']} ({k['sign']}) lo undi "
                 f"mariyu {_state(k, lk)}.")
        rows.append((f"F{len(rows) + 1}", t))
    nxt = len(rows) + 1
    if h["sav"]:
        up = h["sav"] >= 28
        if hi:
            t = (f"{QR._ord(h['number'])} house ka score {h['sav']} hai "
                 f"(average 28 se {'upar' if up else 'neeche'}).")
        else:
            t = (f"{QR._ord(h['number'])} house score {h['sav']} "
                 f"(sarasari 28 kante {'ekkuva' if up else 'takkuva'}).")
        rows.append((f"F{nxt}", t))
        nxt += 1
    p = facts["periods"]
    if p["sub"]:
        t = (f"Aap abhi {p['main']} mahadasha aur {p['sub']} antardasha mein hain." if hi else
             f"Meeru ippudu {p['main']} mahadasha mariyu {p['sub']} antardasha lo unnaru.")
        rows.append((f"F{nxt}", t))
        nxt += 1
    tr = transits(facts, lk)
    if tr:
        rows.append((f"F{nxt}", tr))
    return rows


def timing(facts: dict, lk: str) -> str:
    w = window(facts.get("next_window") or "", lk)
    if not w:
        return ""
    return f"Iske liye sabse anukool samay {w} hai." if lk == "hi_en" else f"Deeniki anukulamaina samayam {w}."


def steps(facts: dict, lk: str) -> list[str]:
    hi = lk == "hi_en"
    key = facts["domain_key"]
    if key == "out_of_domain":
        return []
    if key == "gemstones_remedies":
        out = []
        for r in facts["gems"]["recommended"][:2]:
            finger = _swap(r["finger"].lower(), _FINGER[lk])
            metal = _swap(r["metal"].lower(), _METAL[lk])
            day = _day(r["day"], lk)
            out.append(f"{day} ki subah shukla paksh mein {r['gem']} ko {metal} mein {finger} par pehnein." if hi
                       else f"Shukla pakshamlo {day} udayam {r['gem']} ni {metal} lo {finger} meeda dharinchandi.")
        if facts["gems"]["avoid"]:
            out.append("Avoid wale ratna na pehnein; unke grah ka mantra jaapein aur thoda daan karein." if hi
                       else "Vaddani cheppina ratnalu dharinchakandi; aa graha mantram japinchi konchem danam "
                            "cheyandi.")
        if not out:
            lord = facts["lagna_lord"]
            day = _day(QR._WEEKDAY.get(lord, ""), lk)
            out.append(f"{lord} ka mantra {day or 'uske din'} ko jaapein aur thoda daan dein." if hi
                       else f"{lord} mantram {day or 'aa roju'} japinchi konchem danam cheyandi.")
        return out[:3]
    out = []
    cands = [facts["house"]["lord"], *facts["karakas"]]
    weak = next((c for c in cands if c["hard_house"] or c["dignity"] in QR._BAD_DIGNITY or c["combust"]), None)
    target = weak or (facts["karakas"][0] if facts["karakas"] else None)
    if target:
        k = target["planet"]
        day = _day(QR._WEEKDAY.get(k, ""), lk)
        out.append(f"{k} ko majboot karein: uska mantra jaapein aur {day or 'uske din'} ko thoda daan dein." if hi
                   else f"{k} ni balaparachandi: daani mantram japinchandi mariyu {day or 'aa roju'} na "
                        f"konchem danam cheyandi.")
    w = window(facts.get("next_window") or "", lk)
    if w and key in QR._MOVE_DOMAINS:
        out.append(f"Zaroori kadam {w} ke dauran uthane ka lakshya rakhein aur usse pehle taiyari karein." if hi
                   else f"Mukhyamaina nirnayam {w} lo teesukovadaniki prayatninchandi, daaniki mundu "
                        f"siddham avvandi.")
    return out[:3]


def gem_why(facts: dict, lk: str) -> list[str]:
    hi = lk == "hi_en"
    why = []
    for r in facts["gems"]["recommended"]:
        hs = _AND[lk].join(QR._ord(int(x)) for x in r["houses"])
        why.append(f"{r['planet']} aapke {hs} house ka swami hai, isliye {r['gem']} aapke liye sahayak ratna hai."
                   if hi else
                   f"{r['planet']} mee {hs} house ki adhipati, kabatti {r['gem']} meeku anukulamaina ratnam.")
    for r in facts["gems"]["avoid"][:2]:
        reason = _AVOID_WHY[lk].get(r["reason"], r["reason"])
        why.append(f"{r['gem']} se bachna behtar hai kyunki {reason}." if hi else
                   f"{r['gem']} dharinchakapovadame manchidi, endukante {reason}.")
    return why[:4]


_OPENER = {
    "hi_en": {"favourable": "Aapki kundli is mein saath deti hai.",
              "mixed": "Yeh aapke liye sambhav hai, par thodi mehnat aur deri ke liye taiyar rahein.",
              "difficult": "Abhi aapke liye yeh aasaan nahi hai, lekin raasta band nahi hai."},
    "te_en": {"favourable": "Mee jatakam deeniki maddatu istundi.",
              "mixed": "Idi meeku sadhyame, kani konchem shramam mariyu aalasyam undochchu.",
              "difficult": "Ippudu idi meeku sulabham kaadu, kani daari moosukupoledu."},
}


def answer(facts: dict, stance: str, lk: str) -> str:
    """The short verdict, in the reader's language, built from the facts and the (checked) stance."""
    hi = lk == "hi_en"
    key = facts["domain_key"]
    if key == "out_of_domain":
        return ("Yeh sawal janm kundli ke daayre se bahar lagta hai. Apne career, rishte, paisa, sehat, "
                "parivaar, yatra ya samay ke baare mein poochhein, kundli jawab degi." if hi else
                "Ee prashna jatakam parithi bayata unnattu undi. Mee career, sambandhalu, dabbu, aarogyam, "
                "kutumbam, prayanam leda samayam gurinchi adagandi, jatakam samadhanam istundi.")
    if key == "gemstones_remedies":
        rec, avoid = facts["gems"]["recommended"], facts["gems"]["avoid"]
        if rec:
            names = _AND[lk].join(r["gem"] for r in rec)
            text = (f"Aapke {facts['lagna']} lagna ke liye {names} sabse achha rahega." if hi else
                    f"Mee {facts['lagna']} lagnaniki {names} atyanta anukulam.")
        else:
            text = ("Abhi aapki kundli ke liye koi ratna poori tarah surakshit nahi hai, isliye ratna ki jagah "
                    "mantra aur daan behtar hai." if hi else
                    "Ippudu mee jatakaniki e ratnam poorthiga surakshitam kaadu, kabatti ratnam badulu mantram "
                    "mariyu danam manchidi.")
        if avoid:
            names = ", ".join(r["gem"] for r in avoid[:3])
            text += f" {names} se bachein." if hi else f" {names} dharinchakandi."
        return text
    lord = facts["house"]["lord"]
    dw = _dw(lord["dignity"], lk)
    opener = _OPENER[lk][stance if stance in _OPENER[lk] else "mixed"]
    if hi:
        text = (f"{opener} {lord['planet']}, jo is kshetra ka swami hai, {lord['sign']} mein house "
                f"{lord['house']} mein baitha hai{dw}.")
        if lord["hard_house"]:
            text += " Yeh house kaam ko dheema karta hai."
    else:
        text = (f"{opener} {lord['planet']}, ee rangaaniki adhipati, {lord['sign']} lo house "
                f"{lord['house']} lo undi{dw}.")
        if lord["hard_house"]:
            text += " Aa house panulanu mandagimpachestundi."
    return text
