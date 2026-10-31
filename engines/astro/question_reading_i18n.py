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


def plain_reasons(facts: dict, lk: str) -> list[str]:
    hi = lk == "hi_en"
    key = facts["domain_key"]
    if key == "out_of_domain":
        return []
    if key == "gemstones_remedies":
        asked = facts["gems"].get("asked") or []
        suitable = asked and all(r["verdict"] == "wear" for r in asked)
        first = (("Yeh ratna aapki kundli ke sahayak tathyon se mel khata hai, par trial mein aaram bhi zaroori hai."
                  if suitable else
                  "Yeh ratna aapki kundli ke sahayak tathyon se mel khate hain, par vyaktigat aaram bhi zaroori hai."
                  if not asked else
                  "Jo ratna kisi aur ki kundli ko suit kare, woh aapke liye zaroori nahi; isliye savdhan raasta behtar hai.")
                 if hi else
                 ("Ee ratnam mee jataka anukula amshalatho sardhukuntu undi, ayite trial lo soukaryam kuda mukhyam."
                  if suitable else
                  "Ee ratnalu mee jataka anukula amshalatho sardhukuntayi, ayite vyaktigata soukaryam kuda mukhyam."
                  if not asked else
                  "Inkokari jatakaniki sardina ratnam meeku sardhutundi ani ledu, kabatti jagrattha margam manchidi."))
        second = ("Teen din ka trial sirf savdhani hai, guarantee nahi; asuvidha ho to turant band karein." if hi else
                  "Moodu rojula trial kevalam jagrattha matrame, guarantee kaadu; asoukaryam unte ventane aapeseyandi.")
        return [first, second]
    lenses = facts.get("lenses") or {}
    vuln = lenses.get("vulnerability")
    if vuln:
        import question_health as QH
        body = QH.text_local(vuln, lk).split(" Chandra Naadi", 1)[0].strip()
        care = QR._care_now(facts)
        second = ("Abhi extra dhyan zaroori hai; niyamit dinacharya aur shuruaati dhyaan rakhein." if care else
                  "Abhi sthiti behtar lagti hai, phir bhi niyamit dhyan zaroori hai.") if hi else (
                  "Ippudu ekkuva jagrattha avasaram; kramabaddha dinacharya mariyu mundasthu shraddha patinchandi." if care else
                  "Ippudu paristhiti sthiramga kanipistundi, ayina kramabaddha shraddha avasaram.")
        return [body, second]
    p, _n = QR._verdict_key(facts)
    label = _AREA_LABEL[lk].get(key, "Is sawal" if hi else "Ee prashna")
    if hi:
        first = {1: f"{label} ke liye aapka lambe samay ka pattern sahayak hai.",
                 0: f"{label} ke liye aapka lambe samay ka pattern milajula hai; kuch sahayak aur kuch kathin baatein hain.",
                 -1: f"{label} ke liye aapka lambe samay ka pattern zyada mehnat maangta hai, isliye niyamit koshish zaroori hai."}[p]
        vim = lenses.get("vimshottari") or {}
        second = {"helper": "Abhi ki dasha is sawal se seedhi judi hai, isliye vyavaharik prayas ko saath milta hai.",
                  "hard": "Abhi ki dasha deri ya dabav la sakti hai, isliye pragati dheemi ho sakti hai.",
                  "none": "Abhi ki dasha is sawal ke liye lagbhag tatastha hai, isliye taiyari aur aapke nirnay zyada mahatvapurn hain."}[vim.get("rel", "none")]
    else:
        first = {1: f"{label} kosam mee dirghakalika pattern anukulamga undi.",
                 0: f"{label} kosam mee dirghakalika pattern mishramam; konni anukula, konni kashtamaina amshalu unnayi.",
                 -1: f"{label} kosam mee dirghakalika pattern ekkuva prayatnam korutundi, kabatti nirantara krusi avasaram."}[p]
        vim = lenses.get("vimshottari") or {}
        second = {"helper": "Prastuta dasha ee prashnatho pratyakshamga sambandham kaligi undi, kabatti acharanatmaka prayatnalaku maddatu labhistundi.",
                  "hard": "Prastuta dasha aalasyam leda ottidi techchochu, kabatti pragati mellaga undochu.",
                  "none": "Prastuta dasha ee prashnapai tatasthamga undi, kabatti siddham mariyu mee nirnayalu mukhyam."}[vim.get("rel", "none")]
    rows = [first, second]
    if (lenses.get("naadi") or {}).get("cautions"):
        rows.append("Abhi ka samay sanvedansheel hai; baat-cheet shaant rakhein aur jaldi nirnay na lein." if hi else
                    "Prastuta samayam sunnitamainadi; sambhashana prashantamga unchandi, thvaragatiga nirnayalu teesukokandi.")
    return rows


def timing(facts: dict, lk: str) -> str:
    vuln = (facts.get("lenses") or {}).get("vulnerability")
    if vuln:
        import question_health as QH
        return QH.watch_line(vuln, lk)
    w = window(facts.get("next_window") or "", lk)
    if not w:
        return ""
    return f"Iske liye sabse anukool samay {w} hai." if lk == "hi_en" else f"Deeniki anukulamaina samayam {w}."


def practical_step(facts: dict, has_window: bool, lk: str) -> str:
    hi = lk == "hi_en"
    key = facts["domain_key"]
    q = facts["question"].lower()
    window = "upar dikhaya gaya anukool samay" if hi else "pain chupina anukula samayam"
    if key == "career_profession":
        if "promot" in q:
            return (f"Apne nateeje likhkar rakhein; {window} mein promotion par baat karein." if has_window else
                    "Apne nateeje likhkar rakhein aur manager se promotion par seedhi baat karein.") if hi else (
                    f"Mee phalitalu raasi unchukondi; {window} lo promotion gurinchi matladandi." if has_window else
                    "Mee phalitalu raasi unchukoni manager tho promotion gurinchi pratyakshamga matladandi.")
        if re.search(r"first\s+job|unemployed", q):
            return (f"Focused CV banayein aur interview practice karein; {window} mein applications aur interviews karein." if has_window else
                    "Focused CV banayein, interview practice karein aur lagataar apply karein.") if hi else (
                    f"Focused CV tayar chesi interview practice cheyandi; {window} lo applications mariyu interviews cheyandi." if has_window else
                    "Focused CV tayar chesi interview practice cheyandi, kramamga apply cheyandi.")
        if re.search(r"business|startup|self\s*-?\s*employ", q):
            return (f"Demand jaanchein, budget banayein aur cash cushion rakhein; {window} mein sanyamit launch sochein." if has_window else
                    "Launch se pehle demand jaanchein, budget banayein aur cash cushion rakhein.") if hi else (
                    f"Demand parishilinchi budget tayar chesi cash cushion unchukondi; {window} lo kramamaina launch alochinchandi." if has_window else
                    "Launch kante mundu demand parishilinchi budget tayar chesi cash cushion unchukondi.")
        if "retir" in q:
            return (f"Pension, monthly kharch aur health cover review karein; transition planning {window} mein karein." if has_window else
                    "Retirement date tay karne se pehle pension, monthly kharch aur health cover review karein.") if hi else (
                    f"Pension, nelavari karchu mariyu health cover review cheyandi; transition planning {window} lo cheyandi." if has_window else
                    "Retirement date fix chese mundu pension, nelavari karchu mariyu health cover review cheyandi.")
        if re.search(r"what\s+career|which\s+career|career\s+(?:should|direction)|choose.*career", q):
            return ("Apni ruchi aur strengths ke mutabik kuch career paths tulna karein, phir chhota project ya mentor ki salah lein." if hi else
                    "Mee abhiruchi mariyu strengths batti konni career paths polchandi, tarvata chinna project leda mentor salaha teesukondi.")
        if re.search(r"change|switch|new job|another job", q):
            return (f"CV update karein aur likhit offers tulna karein; {window} mein applications ya switch sochein." if has_window else
                    "CV update karein aur resign karne se pehle likhit offers tulna karein.") if hi else (
                    f"CV update chesi raasthi offers polchandi; {window} lo applications leda switch alochinchandi." if has_window else
                    "CV update chesi resign chese mundu raasthi offers polchandi.")
        if re.search(r"secure|security|safe|layoff|fired|demotion", q):
            return ("Skills update rakhein, apna kaam document karein aur cash cushion banayein." if hi else
                    "Skills update chesukondi, mee pani document chesi cash cushion erparachukondi.")
        return ("Apna kaam document karein aur manager se agla career kadam tay karein." if hi else
                "Mee pani document chesi manager tho tarvati career adugu gurinchi matladandi.")
    if key == "marriage_relationship":
        if re.search(r"marri|wedding|shaadi|vivah", q):
            return (f"{window} mein parichay ya parivaar ki baat-cheet karein, bina jaldi commitment kiye." if has_window else
                    "Parivaar se expectations par khuli baat karein aur jaldi commitment na karein.") if hi else (
                    f"{window} lo parichayalu leda kutumba charchalu cheyandi, thvaragatiga commitment ivvakandi." if has_window else
                    "Kutumbam tho expectations gurinchi terichi matladandi, thvaragatiga commitment ivvakandi.")
        return ("Expectations par ek shaant baat karein aur gusse mein nirnay na lein." if hi else
                "Expectations gurinchi oka prashanta charcha pettandi, kopamlo nirnayalu teesukokandi.")
    if key == "children_progeny":
        return (f"Family planning ke liye {window} ka upyog karein; medical chinta ho to qualified clinician se milein." if has_window else
                "Taiyari aur sehat ko pehle rakhein; medical chinta ho to qualified clinician se milein.") if hi else (
                f"Family planning kosam {window} ni upyoginchandi; medical samasya unte qualified clinician ni sanpradinchandi." if has_window else
                "Siddham mariyu aarogyanni mundu pettandi; medical samasya unte qualified clinician ni sanpradinchandi.")
    if key == "foreign_relocation":
        return (f"Documents aur funds taiyar rakhein; {window} mein visa application ya pakki yatra karein." if has_window else
                "Travel ya relocation commitments karne se pehle documents aur funds taiyar rakhein.") if hi else (
                f"Documents mariyu funds siddham unchandi; {window} lo visa application leda khachitamaina prayanam cheyandi." if has_window else
                "Travel leda relocation commitments kante mundu documents mariyu funds siddham unchandi.")
    if key == "wealth_finances":
        return (f"Savings automate karein aur karz review karein; bade financial commitments {window} mein hi sochein." if has_window else
                "Savings automate karein, karz review karein aur jaldi financial commitments na karein.") if hi else (
                f"Savings automate chesi runalu review cheyandi; pedda financial commitments {window} lo alochinchandi." if has_window else
                "Savings automate chesi runalu review cheyandi, thvaragatiga financial commitments cheyakandi.")
    if key == "education_learning":
        return (f"Taiyari jaldi shuru karein; exams, applications ya submissions ke liye {window} ka upyog karein." if has_window else
                "Niyamit study schedule rakhein aur exam jaise halat mein practice karein.") if hi else (
                f"Siddham munduge modalupettandi; exams, applications leda submissions kosam {window} ni upyoginchandi." if has_window else
                "Kramabaddha study schedule patinchi exam paristhitullo practice cheyandi.")
    if key == "property_assets":
        if re.search(r"sell|sale", q):
            return (f"Title, ownership aur sale documents verify karein; serious buyer discussions {window} mein karein." if has_window else
                    "Offer accept karne se pehle title, ownership aur sale documents verify karein.") if hi else (
                    f"Title, ownership mariyu sale documents verify cheyandi; serious buyer charchalu {window} lo cheyandi." if has_window else
                    "Offer accept chese mundu title, ownership mariyu sale documents verify cheyandi.")
        if re.search(r"transfer|gift", q):
            return ("Property transfer se pehle ownership, tax aur parivaar par asar qualified professional se review karayein." if hi else
                    "Property transfer kante mundu ownership, tax mariyu kutumbam pai prabhavam qualified professional tho review cheyinchukondi.")
        return (f"Title, loan terms aur documents verify karein; serious property steps {window} mein lein." if has_window else
                "Property commitment se pehle title, loan terms aur documents verify karein.") if hi else (
                f"Title, loan terms mariyu documents verify cheyandi; mukhyamaina property steps {window} lo teesukondi." if has_window else
                "Property commitment kante mundu title, loan terms mariyu documents verify cheyandi.")
    if key == "litigation_disputes":
        if "custody" in q:
            return ("Child-focused records rakhein, family lawyer ki salah follow karein aur bachche ko vivad mein na laayein." if hi else
                    "Child-focused records unchukoni family lawyer salaha patinchandi, pillalanu vivadamlo laggakandi.")
        if "divorce" in q:
            return (f"Case aur financial records taiyar rakhein; lawyer ki salah ke saath settlement baat {window} mein karein." if has_window else
                    "Case aur financial records taiyar rakhein aur family lawyer ki salah follow karein.") if hi else (
                    f"Case mariyu financial records siddham unchandi; lawyer salaha tho settlement charchalu {window} lo cheyandi." if has_window else
                    "Case mariyu financial records siddham unchi family lawyer salaha patinchandi.")
        if re.search(r"property|inheritance|tenant|ownership", q):
            return (f"Ownership, payment aur communication records taiyar rakhein; lawyer ki salah ke saath mediation {window} mein karein." if has_window else
                    "Ownership, payment aur communication records taiyar rakhein aur lawyer ki salah follow karein.") if hi else (
                    f"Ownership, payment mariyu communication records siddham unchandi; lawyer salaha tho mediation {window} lo cheyandi." if has_window else
                    "Ownership, payment mariyu communication records siddham unchi lawyer salaha patinchandi.")
        return (f"Documents taiyar rakhein aur lawyer ki salah follow karein; settlement par baat {window} mein karein." if has_window else
                "Settlement tay karne se pehle documents taiyar rakhein aur lawyer ki salah follow karein.") if hi else (
                f"Documents siddham unchi lawyer salaha patinchandi; settlement charchalu {window} lo cheyandi." if has_window else
                "Settlement gurinchi nirnayinche mundu documents siddham unchi lawyer salaha patinchandi.")
    if key == "speech_neurology":
        return ("Qualified speech ya medical professional ke saath niyamit support plan banayein." if hi else
                "Qualified speech leda medical professional tho kramabaddha support plan erparachukondi.")
    if key == "general_destiny":
        return "Ek practical priority chunein aur har mahine pragati review karein." if hi else "Oka practical priority enchukoni prati nelallo pragati review cheyandi."
    return ""


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
            return (f"{r['gem']} ko lagatar pehenne se pehle teen din trial karein. Aaram ho to {day} ki subah shukla "
                    f"paksh mein use {metal} mein {finger} par pehnein." if hi else
                    f"{r['gem']} ni niyamitamga dharinche mundu moodu rojulu trial cheyandi. Soukaryam unte shukla "
                    f"pakshamlo {day} udayam daanini {metal} lo {finger} meeda dharinchandi.")

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
        for r in facts["gems"]["recommended"][:3]:
            finger = _swap(r["finger"].lower(), _FINGER[lk])
            metal = _swap(r["metal"].lower(), _METAL[lk])
            day = _day(r["day"], lk)
            out.append(f"{r['gem']} ko lagatar pehenne se pehle teen din trial karein. Aaram ho to {day} ki subah "
                       f"shukla paksh mein use {metal} mein {finger} par pehnein." if hi else
                       f"{r['gem']} ni niyamitamga dharinche mundu moodu rojulu trial cheyandi. Soukaryam unte shukla "
                       f"pakshamlo {day} udayam daanini {metal} lo {finger} meeda dharinchandi.")
        if facts["gems"]["avoid"] and len(out) < 3:
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
        mantra = QR._MANTRA.get(k, "uska mantra" if hi else "daani mantram")
        out.append(f"{k} ke liye: {day or 'uske din'} ko {mantra} ka 108 baar jaap karein aur thoda daan dein." if hi
                   else f"{k} kosam: {day or 'aa roju'} na {mantra} ni 108 sarlu japinchi konchem danam cheyandi.")
    vuln = (facts.get("lenses") or {}).get("vulnerability")
    if vuln:
        import question_health as QH
        step = QH.prevent_step(vuln, lk)
        if step and QH.sanitized(step):
            out.append(step)
    practical = practical_step(facts, bool(facts.get("next_window") and QR._wants_timing(facts)), lk)
    if practical:
        out.append(practical)
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
        (1, 1): "Aapka lambe samay ka pattern aur abhi ka samay, dono sahayak hain.",
        (1, 0): "Aapka lambe samay ka pattern sahayak hai, par abhi pragati thodi upar-neeche ho sakti hai.",
        (1, -1): "Aapka lambe samay ka pattern sahayak hai, par abhi deri ho sakti hai; sabr aur taiyari zaroori hai.",
        (0, 1): "Picture milajuli hai, par abhi ka samay niyamit koshish ke liye sahayak hai.",
        (0, 0): "Picture milajuli hai, isliye jaldi nateeje ki jagah kuch rukavat sambhav hai.",
        (0, -1): "Picture milajuli hai aur abhi dabav zyada hai; jaldi bada nirnay na lein.",
        (-1, 1): "Pragati mein niyamit mehnat lagegi, par abhi kuch sahayak avsar mil sakte hain.",
        (-1, 0): "Pragati mein dhairya lagega; abhi koi aasaan raasta nahi dikh raha.",
        (-1, -1): "Abhi sthiti kathin lagti hai; jaldi natija paane ki jagah savdhani se aage badhein.",
    },
    "te_en": {
        (1, 1): "Mee dirghakalika pattern mariyu prastuta samayam rendu anukulamga unnayi.",
        (1, 0): "Mee dirghakalika pattern anukulamga undi, kani ippudu pragati konchem upar-neeche undochu.",
        (1, -1): "Mee dirghakalika pattern anukulamga undi, kani ippudu aalasyam undochu; sabram, siddham avasaram.",
        (0, 1): "Paristhiti mishramam, kani prastuta samayam nirantara prayatnaniki anukulam.",
        (0, 0): "Paristhiti mishramam, kabatti thvaragatiga phalitam kante konni aatankalu undochu.",
        (0, -1): "Paristhiti mishramam mariyu ippudu ottidi ekkuva; thvaragatiga pedda nirnayam teesukokandi.",
        (-1, 1): "Pragatiki nirantara krusi avasaram, kani ippudu konni anukula avakashalu undochu.",
        (-1, 0): "Pragatiki opika avasaram; ippudu sulabhamaina margam kanipinchadam ledu.",
        (-1, -1): "Ippudu paristhiti kashtamga undi; thvaragatiga phalitam kante jagratthaga munduku vellandi.",
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
            text = (f"Aapke {facts['lagna']} lagna ke liye {names} behtar vikalp hai." if hi else
                    f"Mee {facts['lagna']} lagnaniki {names} manchi vikalpam.")
        else:
            text = ("Abhi aapki kundli ke liye koi ratna poori tarah surakshit nahi hai, isliye ratna ki jagah "
                    "mantra aur daan behtar hai." if hi else
                    "Ippudu mee jatakaniki e ratnam poorthiga surakshitam kaadu, kabatti ratnam badulu mantram "
                    "mariyu danam manchidi.")
        if avoid:
            names = ", ".join(r["gem"] for r in avoid[:3])
            text += f" {names} se bachein." if hi else f" {names} dharinchakandi."
        return text
    label = _AREA_LABEL[lk].get(key)
    p, n = QR._verdict_key(facts)
    vuln = (facts.get("lenses") or {}).get("vulnerability")
    if vuln:
        import question_health as QH
        care = QR._care_now(facts) or n < 0
        if hi:
            opener = ("Sehat ka lambe samay ka pattern sahayak hai, par abhi extra dhyan aur niyamit dinacharya zaroori hai."
                      if care and p > 0 else
                      "Abhi sehat ka extra dhyan rakhein; niyamit dinacharya banayein aur lagatar takleef ko nazarandaz na karein."
                      if care else
                      "Sehat ko niyamit dhyan chahiye, halanki abhi sthiti sthir lagti hai." if p < 0 else
                      "Abhi sehat kaafi sahayak lagti hai, phir bhi niyamit dhyan zaroori hai.")
        else:
            opener = ("Mee aarogyam dirghakalika pattern anukulam, kani ippudu ekkuva jagrattha mariyu kramabaddha dinacharya avasaram."
                      if care and p > 0 else
                      "Ippudu aarogyam vishayamlo ekkuva jagrattha teesukondi; kramabaddha dinacharya patinchi, nirantara ibbandini nirlakshyam cheyakandi."
                      if care else
                      "Aarogyanki nirantara shraddha avasaram, ayite ippudu paristhiti sthiramga undi." if p < 0 else
                      "Ippudu aarogyam anukulamga kanipistundi, ayina nirantara shraddha avasaram.")
        return f"{opener} {QH.answer_line(vuln, lk)}".strip()
    opener = (f"{label}: " if label else "") + _VERDICT[lk][(p, n)]
    return opener


