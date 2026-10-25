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
        "its planet sits in your 8th house, which stirs up sudden trouble":
            "iska grah aapke 8th house mein baitha hai, jo achanak pareshani laata hai",
        "its planet rules a difficult house (6th, 8th or 12th) and could magnify those problems":
            "iska grah kathin house (6th, 8th ya 12th) ka swami hai aur un samasyaon ko badha sakta hai",
        "its planet rules a house of loss or obstruction for your rising sign":
            "iska grah aapke lagna ke liye haani ya rukawat ke ghar ka swami hai",
        "it is not a safe stone for your chart": "yeh aapki kundli ke liye surakshit ratna nahi hai",
    },
    "te_en": {
        "its planet sits in your 8th house, which stirs up sudden trouble":
            "daani graham mee 8th house lo undi, appudappudu ibbandulu techchi pedutundi",
        "its planet rules a difficult house (6th, 8th or 12th) and could magnify those problems":
            "daani graham kashtamaina house (6th, 8th leda 12th) ki adhipati, aa samasyalanu penchavachchu",
        "its planet rules a house of loss or obstruction for your rising sign":
            "daani graham mee lagnaniki nashtam leda aatankam kaliginche house ki adhipati",
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
                 else " Yeh kamzor sthiti hai, bhale hi house madadgaar hai."
                 if lord["dignity"] in QR._BAD_DIGNITY else " Yeh sahayak sthiti hai."))
    else:
        f1 = (f"{lord['planet']} mee {QR._ord(h['number'])} house ki adhipati, ee prashnanu nadipistundi. "
              f"Adi {lord['sign']} lo house {lord['house']} lo undi{dw}."
              + (" Idi kashtamaina house, aalasyam kaligistundi." if lord["hard_house"]
                 else " Idi balaheenamaina sthiti, house sahayakaramainaa."
                 if lord["dignity"] in QR._BAD_DIGNITY else " Idi anukulamaina sthiti."))
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
    return rows          # periods and transits are judged by their own lenses (see lens_text)


_LENS_WORDS = {
    "hi_en": {"main": "mahadasha", "sub": "antardasha"},
    "te_en": {"main": "mahadasha", "sub": "antardasha"},
}


def _keep_touching(d: dict, jup: str, sat: str) -> tuple[str, str]:
    """A transit that is not touching the house needs no sentence when the other planet is (same rule as English)."""
    if d["jup"]["mode"] == "none" and d["sat"]["mode"] != "none":
        return "", sat
    if d["sat"]["mode"] == "none" and d["jup"]["mode"] != "none":
        return jup, ""
    return jup, sat


def lens_text(key: str, d: dict, facts: dict, lk: str) -> str:
    """Hinglish / Tenglish sentence for one live lens."""
    hi = lk == "hi_en"
    n = QR._ord(int(facts["house"]["number"]))
    if key == "vimshottari":
        who = d["who"]
        if hi:
            base = f"Aap abhi {d['main']} mahadasha aur {d['sub']} antardasha mein hain."
            tail = {"helper": f" {who} un grahon mein se hai jo is sawal ko chalate hain, isliye yeh dasha saath deti hai.",
                    "hard": f" {who} kathin house mein baitha ya uska swami hai, isliye yeh dasha deri aur mehnat laati hai.",
                    "none": f" {who} ka is sawal se seedha sambandh nahi, isliye yeh dasha na dhakelti hai na rokti hai."}
        else:
            base = f"Meeru ippudu {d['main']} mahadasha mariyu {d['sub']} antardasha lo unnaru."
            tail = {"helper": f" {who} ee prashnanu nadipe grahalalo okati, kabatti ee dasha maddatu istundi.",
                    "hard": f" {who} kashtamaina house lo undi leda daani adhipati, kabatti ee dasha aalasyam, shramam techchi pedutundi.",
                    "none": f" {who}ki ee prashnatho nerugaa sambandham ledu, kabatti ee dasha dhakkaadu aapadu."}
        return base + tail[d["rel"]]
    if key == "jaimini":
        head = (f"Aapki Chara dasha ({d['maha']} mahadasha, {d['antar']} antardasha)" if hi else
                f"Mee Chara dasha ({d['maha']} mahadasha, {d['antar']} antardasha)")
        if d["hit"] == "primary":
            return (f"{head} aapke {n} house ki rashi ({d['primary_sign']}) ko jagati hai, jo saath deti hai." if hi else
                    f"{head} mee {n} house rashi ({d['primary_sign']}) ni velugulaki testundi, idi maddatu.")
        if d["hit"] == "lord":
            return (f"{head} {d['lord_sign']} ko jagati hai, jahan aapke {n} house ka swami baitha hai, jo saath deti hai." if hi
                    else f"{head} {d['lord_sign']} ni velugulaki testundi, akkada mee {n} house adhipati undi, idi maddatu.")
        if d["hard"]:
            return (f"{head} aapke {n} house ki rashi ({d['primary_sign']}) tak nahi pahunchti aur usse kathin sthiti mein hai, isliye pragati dheemi hai." if hi
                    else f"{head} mee {n} house rashi ({d['primary_sign']}) ki cheravadam ledu, kashtamaina sthitilo undi, kabatti pragati mellaga untundi.")
        return (f"{head} aapke {n} house ki rashi ({d['primary_sign']}) ko na jagati hai na rokti hai." if hi else
                f"{head} mee {n} house rashi ({d['primary_sign']}) ni velugulaki testadu, aapadu.")
    if key == "yogini":
        head = (f"Yogini: aap {d['name']} ({d['lord']}) dasha mein hain" if hi else
                f"Yogini: meeru {d['name']} ({d['lord']}) dashalo unnaru")
        if d["tone"] == "auspicious":
            return head + ((", jo shubh hai" + (f", aur {d['lord']} bhi is sawal ko chalata hai, jo aur madad karta hai." if d["tie"] else ".")) if hi
                           else (", idi shubhamainadi" + (f", mariyu {d['lord']} kuda ee prashnanu nadipistundi, idi inka maddatu." if d["tie"] else ".")))
        if d["tone"] == "inauspicious":
            return head + ((", jo kasauti ka samay hai" + (f", par {d['lord']} bhi is sawal ko chalata hai, isliye asar kam hota hai." if d["tie"] else ".")) if hi
                           else (", idi pareeksha samayam" + (f", ayite {d['lord']} kuda ee prashnanu nadipistundi, kabatti prabhavam takkuva." if d["tie"] else ".")))
        return head + (", jo milajula hai." if hi else ", idi mishramam.")
    if key == "transit":
        p = QR._ord(int(d["primary"]))
        jh, sh = QR._ord(int(d["jup"]["house"] or 0)), QR._ord(int(d["sat"]["house"] or 0))
        if hi:
            jup = {"in": f"Jupiter aapke {p} house se hi guzar raha hai, jo use aashirwad deta hai",
                   "aspects": f"Jupiter, aapke {jh} house se, {p} house ko dekhta hai aur saath deta hai",
                   "none": f"Jupiter, aapke {jh} house mein, {p} house ko nahi chhu raha"}.get(d["jup"]["mode"], "")
            sat = {"in": f"Shani aapke {p} house se hi guzar raha hai, jo use dheema karta hai aur parakhta hai",
                   "aspects": f"Shani, aapke {sh} house se, {p} house ko dekhta hai aur dabav badhata hai",
                   "none": f"Shani, aapke {sh} house mein, {p} house par dabav nahi daal raha"}.get(d["sat"]["mode"], "")
            text = "Gochar: " + "; ".join(x for x in _keep_touching(d, jup, sat) if x) + "."
            if d["nodes"]:
                text += f" Rahu aur Ketu aapke {p} house ke axis par hain, jo use asthir karte hain."
        else:
            jup = {"in": f"Jupiter mee {p} house gunda ade sancharistunnadu, adi deeniki asheervadam",
                   "aspects": f"Jupiter, mee {jh} house nundi, {p} house ni choosi maddatu istunnadu",
                   "none": f"Jupiter, mee {jh} house lo, {p} house ni thakadam ledu"}.get(d["jup"]["mode"], "")
            sat = {"in": f"Shani mee {p} house gunda ade sancharistunnadu, adi deeniki aalasyam, pareeksha",
                   "aspects": f"Shani, mee {sh} house nundi, {p} house ni choosi ottidi penchutunnadu",
                   "none": f"Shani, mee {sh} house lo, {p} house meeda ottidi teevatam ledu"}.get(d["sat"]["mode"], "")
            text = "Gochar: " + "; ".join(x for x in _keep_touching(d, jup, sat) if x) + "."
            if d["nodes"]:
                text += f" Rahu mariyu Ketu mee {p} house axis lo unnaru, idi deenini asthiram chestundi."
        return text
    if key == "naadi":
        import question_naadi as QN
        return QN.text_local(d, facts, lk)
    if key == "vulnerability":
        import question_health as QH
        return QH.text_local(d, lk)
    return ""


def timing(facts: dict, lk: str) -> str:
    vuln = (facts.get("lenses") or {}).get("vulnerability")
    if vuln:
        import question_health as QH
        return QH.watch_line(vuln, lk)
    w = window(facts.get("next_window") or "", lk)
    if not w:
        return ""
    return f"Iske liye sabse anukool samay {w} hai." if lk == "hi_en" else f"Deeniki anukulamaina samayam {w}."


def steps(facts: dict, lk: str) -> list[str]:
    hi = lk == "hi_en"
    key = facts["domain_key"]
    if key == "out_of_domain":
        return []
    if key == "gemstones_remedies" and facts["gems"].get("asked"):
        out = []

        def wear_line(r: dict) -> str:
            finger = _swap(r["finger"].lower(), _FINGER[lk])
            metal = _swap(r["metal"].lower(), _METAL[lk])
            day = _day(r["day"], lk)
            return (f"{day} ki subah shukla paksh mein {r['gem']} ko {metal} mein {finger} par pehnein." if hi
                    else f"Shukla pakshamlo {day} udayam {r['gem']} ni {metal} lo {finger} meeda dharinchandi.")

        for r in facts["gems"]["asked"]:
            if r["verdict"] == "wear":
                out.append(wear_line(r))
            else:
                day = _day(QR._WEEKDAY.get(r["planet"], ""), lk)
                out.append(f"{r['gem']} na pehnein; {r['planet']} ka mantra jaapein aur {day or 'uske din'} ko thoda daan dein."
                           if hi else
                           f"{r['gem']} dharinchakandi; {r['planet']} mantram japinchi {day or 'aa roju'} na konchem danam cheyandi.")
        skip = {r["planet"] for r in facts["gems"]["asked"]}
        for r in [x for x in facts["gems"]["recommended"] if x["planet"] not in skip][:1]:
            out.append(("Agar ratna pehenna ho to: " if hi else "Ratnam kavalante: ") + wear_line(r))
        return out[:3]
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
    vuln = (facts.get("lenses") or {}).get("vulnerability")
    if vuln:
        import question_health as QH
        step = QH.prevent_step(vuln, lk)
        if step and QH.sanitized(step):
            out.append(step)
    w = window(facts.get("next_window") or "", lk)
    if w and key in QR._MOVE_DOMAINS:
        out.append(f"Zaroori kadam {w} ke dauran uthane ka lakshya rakhein aur usse pehle taiyari karein." if hi
                   else f"Mukhyamaina nirnayam {w} lo teesukovadaniki prayatninchandi, daaniki mundu "
                        f"siddham avvandi.")
    return out[:3]


def _place(r: dict, lk: str) -> str:
    hs = _AND[lk].join(QR._ord(int(x)) for x in r["houses"])
    if lk == "hi_en":
        rules = (f"{r['planet']} aapke {hs} house ka swami hai" if r["houses"]
                 else f"{r['planet']} aapke lagna ke liye kisi house ka swami nahi hai")
        return rules + (f" aur house {r['in_house']} mein baitha hai" if r.get("in_house") else "")
    rules = (f"{r['planet']} mee {hs} house ki adhipati" if r["houses"]
             else f"{r['planet']} mee lagnaniki e house ki adhipati kaadu")
    return rules + (f" mariyu house {r['in_house']} lo undi" if r.get("in_house") else "")


def asked_why(r: dict, lk: str) -> str:
    hi = lk == "hi_en"
    place = _place(r, lk)
    if r["verdict"] == "wear":
        return (f"{place}, isliye {r['gem']} aapke liye sahayak ratna hai." if hi else
                f"{place}, kabatti {r['gem']} meeku anukulamaina ratnam.")
    if r["verdict"] == "avoid":
        reason = _AVOID_WHY[lk].get(r["reason"], r["reason"])
        return (f"{r['gem']} se bachna behtar hai kyunki {reason} ({place})." if hi else
                f"{r['gem']} dharinchakapovadame manchidi, endukante {reason} ({place}).")
    return (f"{place}. Aapke lagna ke liye yeh aisa grah nahi jiska ratna pehenna surakshit ho, isliye mantra "
            f"aur daan behtar hai." if hi else
            f"{place}. Mee lagnaniki ee grahaniki ratnam dharinchadam surakshitam kaadu, kabatti mantram "
            f"mariyu danam manchidi.")


def asked_answer(facts: dict, lk: str) -> str:
    hi = lk == "hi_en"
    parts = []
    for r in facts["gems"]["asked"]:
        g = r["gem"]
        parts.append({
            "wear": f"{g} aapke liye theek hai." if hi else f"{g} meeku anukulam.",
            "avoid": f"{g} se bachein." if hi else f"{g} dharinchakandi.",
            "mantra": (f"{g} pehenne ki salah nahi hai; {r['planet']} ka mantra aur daan behtar hai." if hi else
                       f"{g} dharinchadam salaha kaadu; {r['planet']} mantram mariyu danam manchidi."),
        }[r["verdict"]])
    skip = {r["planet"] for r in facts["gems"]["asked"]}
    others = [r["gem"] for r in facts["gems"]["recommended"] if r["planet"] not in skip]
    if others and not all(r["verdict"] == "wear" for r in facts["gems"]["asked"]):
        names = _AND[lk].join(others)
        parts.append(f"Aapke liye behtar ratna: {names}." if hi else f"Meeku manchi ratnalu: {names}.")
    return " ".join(parts)


def gem_why(facts: dict, lk: str) -> list[str]:
    hi = lk == "hi_en"
    asked = facts["gems"].get("asked", [])
    why = [asked_why(r, lk) for r in asked]
    skipped = {r["planet"] for r in asked}
    for r in facts["gems"]["recommended"]:
        if r["planet"] in skipped:
            continue
        hs = _AND[lk].join(QR._ord(int(x)) for x in r["houses"])
        why.append(f"{r['planet']} aapke {hs} house ka swami hai, isliye {r['gem']} aapke liye sahayak ratna hai."
                   if hi else
                   f"{r['planet']} mee {hs} house ki adhipati, kabatti {r['gem']} meeku anukulamaina ratnam.")
    for r in facts["gems"]["avoid"][:2]:
        if r["planet"] in skipped:
            continue
        reason = _AVOID_WHY[lk].get(r["reason"], r["reason"])
        why.append(f"{r['gem']} se bachna behtar hai kyunki {reason}." if hi else
                   f"{r['gem']} dharinchakapovadame manchidi, endukante {reason}.")
    return why[:5 if asked else 4]


_VERDICT = {
    "hi_en": {
        (1, 1): "Aapki kundli ka vachan is mein saath deta hai aur abhi chal rahi dasha bhi saath hai.",
        (1, 0): "Aapki kundli ka vachan is mein saath deta hai, aur abhi chal rahi dasha milijuli hai, isliye lagatar koshish kaam aayegi.",
        (1, -1): "Aapki kundli ka vachan is mein saath deta hai, par abhi chal rahi dasha ise rok rahi hai, isliye sabr rakhein.",
        (0, 1): "Aapki kundli ka vachan yahan milajula hai, par abhi chal rahi dasha madad kar rahi hai.",
        (0, 0): "Yeh aapke liye sambhav hai, par thodi mehnat aur deri ke liye taiyar rahein.",
        (0, -1): "Aapki kundli ka vachan yahan milajula hai, aur abhi chal rahi dasha rukawat badha rahi hai.",
        (-1, 1): "Aapki kundli ka vachan yahan kamzor hai, par abhi chal rahi dasha madad karti hai, isliye ab mehnat rang laayegi.",
        (-1, 0): "Aapki kundli ka vachan yahan kamzor hai aur abhi chal rahi dasha milijuli hai, isliye mehnat lagegi.",
        (-1, -1): "Abhi aapke liye yeh aasaan nahi hai: kundli ka vachan kamzor hai aur abhi chal rahi dasha rukawat badha rahi hai.",
    },
    "te_en": {
        (1, 1): "Mee jatakam vagdanam deeniki maddatu istundi, ippudu nadustunna dasha kuda saha ayam chestundi.",
        (1, 0): "Mee jatakam vagdanam deeniki maddatu istundi, ippudu nadustunna dasha mishramam, kabatti nirantara prayatnam phalistundi.",
        (1, -1): "Mee jatakam vagdanam deeniki maddatu istundi, kani ippudu nadustunna dasha daanini aapestondi, kabatti sabaram avasaram.",
        (0, 1): "Mee jatakam vagdanam ikkada mishramam, kani ippudu nadustunna dasha maddatu istundi.",
        (0, 0): "Idi meeku sadhyame, kani konchem shramam mariyu aalasyam undochchu.",
        (0, -1): "Mee jatakam vagdanam ikkada mishramam, mariyu ippudu nadustunna dasha ibbandi penchutundi.",
        (-1, 1): "Mee jatakam vagdanam ikkada balaheenam, kani ippudu nadustunna dasha maddatu istundi, kabatti ippudu prayatnam phalistundi.",
        (-1, 0): "Mee jatakam vagdanam ikkada balaheenam, ippudu nadustunna dasha mishramam, kabatti shramam kavali.",
        (-1, -1): "Ippudu idi meeku sulabham kaadu: jatakam vagdanam balaheenam, mariyu ippudu nadustunna dasha ibbandi penchutundi.",
    },
}


_AREA_LABEL = {
    "hi_en": {"health_vitality": "Sehat", "career_profession": "Career", "marriage_relationship": "Rishta",
              "wealth_finances": "Paisa", "children_progeny": "Santan", "education_learning": "Padhai",
              "foreign_relocation": "Videsh yatra", "property_assets": "Property",
              "litigation_disputes": "Vivad", "speech_neurology": "Vaani aur naadi",
              "general_destiny": "Jeevan path"},
    "te_en": {"health_vitality": "Aarogyam", "career_profession": "Career", "marriage_relationship": "Sambandham",
              "wealth_finances": "Dabbu", "children_progeny": "Santanam", "education_learning": "Chaduvu",
              "foreign_relocation": "Videsha prayanam", "property_assets": "Property",
              "litigation_disputes": "Vivadam", "speech_neurology": "Maatalu mariyu narallu",
              "general_destiny": "Jeevana margam"},
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
    if key == "gemstones_remedies" and facts["gems"].get("asked"):
        return asked_answer(facts, lk)
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
    label = _AREA_LABEL[lk].get(key)
    opener = (f"{label}: " if label else "") + _VERDICT[lk][QR._verdict_key(facts)]
    vuln = (facts.get("lenses") or {}).get("vulnerability")
    if vuln:                  # health: where to take care, instead of repeating the ruling planet
        import question_health as QH
        return f"{opener} {QH.answer_line(vuln, lk)}".strip()
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


