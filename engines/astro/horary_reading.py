"""A horary question answered in the same one-card format as the natal question report.

The natal question report judges one question through several lenses, turns
each into a vote, and shows: a short answer, the lens chips, a few plain
reasons, then (paid) when and what to do. A horary used to get a different
page. This module gives it the same one, with the lenses a moment chart has:

* ``kp``       the cuspal sub-lord's promise (houses it helps vs houses it denies)
* ``ruling``   do the planets ruling the moment match the planets that decide the matter
* ``period``   does a period that can deliver this run now or open soon
* ``moment``   the Prashna chart cast for the moment
* ``jamakkol`` the Jamakkol reading of the same moment
* ``moon``     the Moon of the moment (Chandra), its phase and place

The verdict itself is still the model's: ``judge_kp_horary`` labels the
question and ``write_plain_answer`` words it. The votes are fixed rules, so a
reader can see how the chart lined up, and they may soften a label (never
turn a "no" into a "yes").
"""
from __future__ import annotations

import html
from typing import Any, Optional

import question_reading as QR

LENS_ORDER = ("kp", "ruling", "period", "moment", "jamakkol", "moon")

_DUSTHANA = {6, 8, 12}

# What a house stands for, said without the word "house" and with no "and" inside a
# label (the labels are joined into a list). A few houses read differently when they
# HELP the matter (service helps a job) than when they work against it (strain).
_HOUSE = {
    "en": {1: "your wellbeing", 2: "money", 3: "effort", 4: "home", 5: "luck and learning",
           6: "strain", 7: "partnership", 8: "sudden change", 9: "fortune", 10: "career",
           11: "gains", 12: "expense"},
    "hi_en": {1: "aapki sehat", 2: "dhan", 3: "prayas", 4: "ghar", 5: "bhagya aur vidya",
              6: "tanav", 7: "saajhedari", 8: "achanak badlav", 9: "bhagya", 10: "career",
              11: "labh", 12: "kharch"},
    "te_en": {1: "mee aarogyam", 2: "dhanam", 3: "prayatnam", 4: "illu", 5: "adrushtam mariyu vidya",
              6: "ibbandi", 7: "bhagaswamyam", 8: "akasmika marpu", 9: "adrushtam", 10: "career",
              11: "labham", 12: "kharchu"},
}
_HOUSE_HELPS = {
    "en": {6: "service", 8: "sudden turns that help", 12: "distance and travel"},
    "hi_en": {6: "seva", 8: "achanak madad", 12: "doori aur yatra"},
    "te_en": {6: "seva", 8: "akasmika sahayam", 12: "duram mariyu prayanam"},
}
_AND = {"en": " and ", "hi_en": " aur ", "te_en": " mariyu "}


def _clamp(n: int) -> int:
    return max(-1, min(1, n))


def _ints(values: Any) -> list[int]:
    out: list[int] = []
    for v in values or []:
        try:
            out.append(int(str(v).strip()))
        except (TypeError, ValueError):
            continue
    return out


# --------------------------------------------------------------------------- votes
def _kp(ev: dict) -> dict:
    fav, den = _ints(ev.get("fav_hits")), _ints(ev.get("den_hits"))
    diff = len(fav) - len(den)
    if diff > 0 and (not den or len(fav) >= 2 * len(den)):
        vote = 1
    elif diff < 0:
        vote = -1
    else:
        vote = 0
    return {"vote": vote, "fav": fav, "den": den, "bhava": int(ev.get("primary_bhava") or 0)}


def _ruling(ev: dict) -> Optional[dict]:
    ruling = [str(p) for p in ev.get("ruling_planets") or []]
    decide = [str(p) for p in (ev.get("list_c") or ev.get("list_a") or [])]
    if not ruling or not decide:
        return None
    both = [p for p in decide if p in ruling]
    sub = str(ev.get("cusp_sub_lord") or "")
    if len(both) >= 3 or (sub in ruling and len(both) >= 2):
        vote = 1
    elif not both:
        vote = -1
    else:
        vote = 0
    return {"vote": vote, "agree": both}


def _period(timing: dict) -> dict:
    if not timing or timing.get("beyond_horizon") or not timing.get("window"):
        return {"vote": -1, "near": False}
    near = bool(timing.get("near")) or int(timing.get("days_away", 999)) <= 400
    return {"vote": 1 if near else 0, "near": near}


def _moment(data: dict) -> Optional[dict]:
    p = data.get("prashna") or {}
    label = str(p.get("label") or "").upper()
    if not label:
        return None
    if label.startswith("YES"):
        vote = 1
    elif label.startswith("NO"):
        vote = -1
    else:
        score = float(p.get("score") or 0.0)
        vote = 1 if score > 0.35 else -1 if score < -0.35 else 0
    return {"vote": vote, "label": label}


def _jamakkol(data: dict) -> Optional[dict]:
    verdict = str((data.get("jamakkol") or {}).get("verdict") or "").upper()
    if not verdict:
        return None
    vote = 1 if verdict.startswith("YES") else -1 if verdict.startswith("NO") else 0
    return {"vote": vote, "verdict": verdict}


def _moon(data: dict, ev: dict) -> Optional[dict]:
    moon = (data.get("planets") or {}).get("Moon") or {}
    if not moon:
        return None
    house = int((data.get("houses") or {}).get("Moon") or 0)
    bright = bool(((data.get("meta") or {}).get("paksha") or {}).get("bright_moon"))
    star_in = str(moon.get("star_lord") or "") in {str(p) for p in ev.get("list_c") or []}
    score = (1 if bright else -1) + (-1 if house in _DUSTHANA else 1 if house else 0) + (1 if star_in else 0)
    vote = 1 if score >= 2 else -1 if score <= -1 else 0
    return {"vote": vote, "bright": bright, "strained": house in _DUSTHANA, "house": house,
            "sign": moon.get("sign") or "", "nakshatra": moon.get("nakshatra") or ""}


def build_lenses(data: Optional[dict], ev: dict, timing: Optional[dict]) -> dict[str, dict]:
    """Every lens the data supports; a missing source leaves its lens out rather than guessing."""
    data = data or {}
    out: dict[str, dict] = {"kp": _kp(ev)}
    for key, got in (("ruling", _ruling(ev)), ("period", _period(timing or {})),
                     ("moment", _moment(data)), ("jamakkol", _jamakkol(data)),
                     ("moon", _moon(data, ev))):
        if got is not None:
            out[key] = got
    return out


def score(lenses: dict[str, dict]) -> int:
    return 2 * lenses.get("kp", {}).get("vote", 0) + sum(
        v.get("vote", 0) for k, v in lenses.items() if k != "kp")


def promise_and_now(lenses: dict[str, dict]) -> tuple[int, int]:
    p = lenses.get("kp", {}).get("vote", 0)
    live = sum(v.get("vote", 0) for k, v in lenses.items() if k != "kp")
    return p, (1 if live >= 2 else -1 if live <= -2 else 0)


def confidence(lenses: dict[str, dict], data: Optional[dict] = None) -> str:
    s = score(lenses)
    sign = 1 if s > 0 else -1 if s < 0 else 0
    against = sum(1 for v in lenses.values() if sign and v.get("vote", 0) == -sign)
    if int(((data or {}).get("radicality") or {}).get("score") or 0) >= 3:
        return "low"                    # the moment looks casual or a test: say so, do not sound sure
    if abs(s) >= 4 and against == 0:
        return "high"
    return "low" if abs(s) <= 1 else "moderate"


def outlook(lenses: dict[str, dict]) -> str:
    """Which way the lenses lean overall: "for", "against" or "" when mixed."""
    s = score(lenses)
    return "for" if s >= 3 else "against" if s <= -3 else ""


def stance(label: str, lenses: dict[str, dict]) -> str:
    """The model's label sets the outlook; the votes may soften it by one step, never flip it."""
    if label == "out_of_scope":
        return "not_astrological"
    s = score(lenses)
    if label == "yes":
        return "mixed" if s <= -2 else "favourable"
    if label == "no":
        return "mixed" if s >= 3 else "difficult"
    return "favourable" if s >= 3 else "difficult" if s <= -3 else "mixed"


# ----------------------------------------------------------------------------- words
_BECAUSE = {
    "en": {
        (1, 1): "Both the chart's promise and the moment back it.",
        (1, 0): "The chart's promise is good, but the moment is mixed.",
        (1, -1): "The chart's promise is good, but the moment is holding it back.",
        (0, 1): "The chart's promise is mixed, but the moment helps.",
        (0, 0): "The chart's promise and the moment are both mixed.",
        (0, -1): "The chart's promise is mixed and the moment adds friction.",
        (-1, 1): "The chart's promise is weak, though the moment helps.",
        (-1, 0): "The chart's promise is weak and the moment is mixed.",
        (-1, -1): "Both the chart's promise and the moment are against it.",
    },
    "hi_en": {
        (1, 1): "Kundli ka vachan aur yeh samay, dono iske paksh mein hain.",
        (1, 0): "Kundli ka vachan achha hai, par yeh samay milajula hai.",
        (1, -1): "Kundli ka vachan achha hai, par yeh samay ise rok raha hai.",
        (0, 1): "Kundli ka vachan milajula hai, par yeh samay madad karta hai.",
        (0, 0): "Kundli ka vachan aur yeh samay, dono milejule hain.",
        (0, -1): "Kundli ka vachan milajula hai aur yeh samay rukawat badhata hai.",
        (-1, 1): "Kundli ka vachan kamzor hai, halanki yeh samay madad karta hai.",
        (-1, 0): "Kundli ka vachan kamzor hai aur yeh samay milajula hai.",
        (-1, -1): "Kundli ka vachan aur yeh samay, dono iske khilaf hain.",
    },
    "te_en": {
        (1, 1): "Kundali vagdanam mariyu ee samayam, rendu deeniki anukoolam.",
        (1, 0): "Kundali vagdanam bagundi, kani ee samayam mishramam.",
        (1, -1): "Kundali vagdanam bagundi, kani ee samayam deenini aaputhundi.",
        (0, 1): "Kundali vagdanam mishramam, kani ee samayam sahayam chesthundi.",
        (0, 0): "Kundali vagdanam mariyu ee samayam, rendu mishramam.",
        (0, -1): "Kundali vagdanam mishramam, ee samayam adankulu penchuthundi.",
        (-1, 1): "Kundali vagdanam balahinam, ayinaa ee samayam sahayam chesthundi.",
        (-1, 0): "Kundali vagdanam balahinam, ee samayam mishramam.",
        (-1, -1): "Kundali vagdanam mariyu ee samayam, rendu deeniki vyatirekam.",
    },
}

_MOON_WHO = {"en": "The Moon, which shows your state of mind at this moment,",
             "hi_en": "Chandra, jo is samay aapke mann ki sthiti dikhata hai,",
             "te_en": "Chandrudu, ee samayamlo mee manassthiti chupisthadu,"}

_TEXT = {
    "en": {
        "kp+": "The chart's deciding point backs this: it links to {fav}{den_tail}.",
        "kp-": "The chart's deciding point works against this: it links to {den}.",
        "kp0": "The chart's deciding point is mixed: it links to {fav}, but also to {den}.",
        "kp00": "The chart's deciding point is neutral and does not settle it.",
        "den_tail": ", though it also touches {den}",
        "ruling+": "The planets ruling this moment line up with the ones that decide the matter.",
        "ruling0": "Only some of the planets ruling this moment line up with the matter.",
        "ruling-": "None of the planets ruling this moment line up with the matter.",
        "period+": "A period that can deliver this is running now or opens within the year.",
        "period0": "A period that can deliver this exists, but it opens later.",
        "period-": "No period in the next few years clearly opens for this.",
        "moment+": "The chart cast for this exact moment leans in your favour.",
        "moment0": "The chart cast for this exact moment is balanced: its strengths and strains offset each other.",
        "moment-": "The chart cast for this exact moment leans against it.",
        "jamakkol+": "A second, independent method from Tamil tradition, read from the same moment, agrees.",
        "jamakkol0": "A second, independent method from Tamil tradition, read from the same moment, "
                     "gives no clear lean.",
        "jamakkol-": "A second, independent method from Tamil tradition, read from the same moment, "
                     "points the other way.",
        "moon+": "{who} is bright and comfortably placed, which steadies things.",
        "moon0": "{who} gives a mixed signal: {mix}.",
        "moon-": "{who} is waning and strained, so avoid deciding in a hurry.",
        "mix_a": "bright but strained", "mix_b": "waning but comfortably placed", "mix_c": "neither strong nor weak",
    },
    "hi_en": {
        "kp+": "Kundli ka nirnayak sanket iske paksh mein hai: yeh {fav} se juda hai{den_tail}.",
        "kp-": "Kundli ka nirnayak sanket iske khilaf hai: yeh {den} se juda hai.",
        "kp0": "Kundli ka nirnayak sanket milajula hai: yeh {fav} se juda hai, par {den} se bhi.",
        "kp00": "Kundli ka nirnayak sanket tatasth hai aur ise tay nahi karta.",
        "den_tail": ", halanki yeh {den} ko bhi chhoota hai",
        "ruling+": "Is samay ke shasak grah usi se mel khate hain jo is baat ko tay karte hain.",
        "ruling0": "Is samay ke kuch hi shasak grah is baat se mel khate hain.",
        "ruling-": "Is samay ka koi bhi shasak grah is baat se mel nahi khata.",
        "period+": "Ise dene wali dasha abhi chal rahi hai ya saal ke andar shuru hogi.",
        "period0": "Ise dene wali dasha hai, par woh baad mein shuru hoti hai.",
        "period-": "Agle kuch varshon mein koi dasha saaf taur par iske liye nahi khulti.",
        "moment+": "Is hi kshan ki prashna kundli aapke paksh mein jhukti hai.",
        "moment0": "Is hi kshan ki prashna kundli santulit hai: uski taakat aur kamzori ek doosre ko kaat deti hain.",
        "moment-": "Is hi kshan ki prashna kundli iske khilaf jhukti hai.",
        "jamakkol+": "Tamil parampara ki ek doosri swatantra vidhi, usi kshan se padhi gayi, bhi sehmat hai.",
        "jamakkol0": "Tamil parampara ki ek doosri swatantra vidhi, usi kshan se padhi gayi, "
                     "koi saaf jhukav nahi deti.",
        "jamakkol-": "Tamil parampara ki ek doosri swatantra vidhi, usi kshan se padhi gayi, "
                     "ulta sanket deti hai.",
        "moon+": "{who} ujjwal aur aaramdayak sthiti mein hai, jo mamle ko sthir karta hai.",
        "moon0": "{who} milajula sanket deta hai: {mix}.",
        "moon-": "{who} ghat raha hai aur tanav mein hai, isliye jaldbaazi mein faisla na lein.",
        "mix_a": "ujjwal par tanav mein", "mix_b": "ghatta hua par aaramdayak", "mix_c": "na mazboot na kamzor",
    },
    "te_en": {
        "kp+": "Kundali nirnayaka sanketam deeniki anukoolam: idi {fav} tho mudipadi undi{den_tail}.",
        "kp-": "Kundali nirnayaka sanketam deeniki vyatirekam: idi {den} tho mudipadi undi.",
        "kp0": "Kundali nirnayaka sanketam mishramam: idi {fav} tho, ayinaa {den} tho kuda mudipadi undi.",
        "kp00": "Kundali nirnayaka sanketam tatasthamga undi, deeni nirnayinchadu.",
        "den_tail": ", ayite idi {den} ni kuda thaakuthundi",
        "ruling+": "Ee samayam shasinche grahalu ee vishayanni nirnayinche grahalatho kalusthunnayi.",
        "ruling0": "Ee samayam shasinche grahalalo konni matrame ee vishayatho kalusthunnayi.",
        "ruling-": "Ee samayam shasinche grahalalo okkati kuda ee vishayatho kalavadu.",
        "period+": "Deenini ichche dasha ippudu nadustondi leda ee edululoga modalavuthundi.",
        "period0": "Deenini ichche dasha undi, kani adi tarvata modalavuthundi.",
        "period-": "Mundu konni samvatsaralalo ee paniki spashtamaina dasha ledu.",
        "moment+": "Ee kshanam chart mee vaipu mogguchuputhondi.",
        "moment0": "Ee kshanam chart samathulyam: daani balalu, balaheenatalu okadanni okati taggisthayi.",
        "moment-": "Ee kshanam chart deeniki vyatirekanga undi.",
        "jamakkol+": "Tamil sampradayamlo maro swatantra paddhati, ade kshanam nundi chadivite, kuda angeekaristhundi.",
        "jamakkol0": "Tamil sampradayamlo maro swatantra paddhati, ade kshanam nundi chadivite, "
                     "spashtamaina mogguni ivvadu.",
        "jamakkol-": "Tamil sampradayamlo maro swatantra paddhati, ade kshanam nundi chadivite, "
                     "viruddha sanketam istundi.",
        "moon+": "{who} prakashavantamga, sowkaryamga undi, ide visayanni sthiramga unchuthundi.",
        "moon0": "{who} mishra sanketam istundi: {mix}.",
        "moon-": "{who} kshinisthu, ibbandilo undi, anduke tondaraga nirnayam teesukovaddu.",
        "mix_a": "prakashavantam kani ibbandilo", "mix_b": "kshinisthu kani sowkaryamga",
        "mix_c": "balam kaadu, balaheenam kaadu",
    },
}


def _meanings(houses: list[int], lk: str, helps: bool = False) -> str:
    table = {**_HOUSE[lk], **(_HOUSE_HELPS[lk] if helps else {})}
    words = [table[h] for h in dict.fromkeys(houses) if h in table][:3]
    return QR._and_join(words) if lk == "en" else (
        ", ".join(words[:-1]) + _AND[lk] + words[-1] if len(words) > 1 else "".join(words))


def lens_text(key: str, d: dict, lk: str) -> str:
    T = _TEXT[lk]
    v = int(d.get("vote", 0))
    mark = {1: "+", 0: "0", -1: "-"}[v]
    if key == "kp":
        fav, den = _meanings(d["fav"], lk, helps=True), _meanings(d["den"], lk)
        if v == 1:
            return T["kp+"].format(fav=fav, den_tail=T["den_tail"].format(den=den) if den else "")
        if v == -1:
            return T["kp-"].format(den=den or _meanings(d["den"] or [d["bhava"]], lk))
        return T["kp0"].format(fav=fav, den=den) if fav and den else T["kp00"]
    if key == "moon":
        bright, strained = bool(d.get("bright")), bool(d.get("strained"))
        mix = T["mix_a"] if bright and strained else T["mix_b"] if not bright and not strained else T["mix_c"]
        return T[f"moon{mark}"].format(who=_MOON_WHO[lk], mix=mix)
    return T[f"{key}{mark}"]


def because(lenses: dict[str, dict], lk: str) -> str:
    return _BECAUSE[lk][promise_and_now(lenses)]


# Hindi/Telugu wording is fixed: the 7B model answers in English whatever it is told.
_GLOSS_LOCAL = {
    "hi_en": {
        "yes": "Haan, kundli ise sahi tehraati hai.",
        "no": "Nahi, kundli ise samarthan nahi deti.",
        "conditional": {"against": "Abhi yeh sambhav nahi lagta.",
                        "for": "Yeh sambhav lagta hai, par pakka nahi.",
                        "": "Abhi koi pakka haan ya na nahi hai; yeh sthiti par nirbhar karta hai."},
        "open": "Kundli abhi ise poori tarah tay nahi karti.",
        "quantity": "Is tarah ki kundli koi sankhya nahi bata sakti; woh sirf itna bata sakti hai ki baat "
                    "aage badhegi ya nahi.",
        "out_of_scope": "Yeh prashna prashna-jyotish ke daayre se bahar hai.",
    },
    "te_en": {
        "yes": "Avunu, kundali deenini samarthisthundi.",
        "no": "Kaadu, kundali deenini samarthinchadu.",
        "conditional": {"against": "Ippudu idi sambhavam anipinchadu.",
                        "for": "Idi sambhavamga kanipisthundi, kani khachchitam kaadu.",
                        "": "Ippudu khachchitamaina avunu leda kaadu ledu; idi paristhitipai aadharapadi untundi."},
        "open": "Kundali deenini ippudu purtiga nirnayinchadu.",
        "quantity": "Ilanti kundali edi sankhyanu cheppaledu; adi kevalam pani mundukelthundo ledo matrame "
                    "cheppagaladu.",
        "out_of_scope": "Ee prashna prashna-jyotishyam paridhiki bayata undi.",
    },
}

_REMEDY_LOCAL = {
    "hi_en": {
        "Saturn": "Dheema, jaanch-yogya kaam pehle karein: sab kuch likhit mein lein aur taalte aaye deadline poori karein.",
        "Mars": "Garmi kam karein. Ek hafte is par bahes na karein aur doosre paksh ko pehle badhne dein.",
        "Sun": "Seedha us vyakti se milein jo faisla kar sakta hai; neeche ke star par yeh atka rehta hai.",
        "Moon": "Is hafte faisla na lein. Kuch hi dinon mein aapki soch badlegi, isliye pehle man ko shant hone dein.",
        "Mercury": "Sab kuch likhit mein karein aur jo pehle bheja hai use dobara padhein; galatfehmi shabdon mein hai.",
        "Venus": "Dobara maangne se pehle rishta sudharein. Log prastav ko nahi, vyakti ko haan kehte hain.",
        "Jupiter": "Kisi varishth se aapki taraf se baat karne ko kahein; yeh sifarish se khulta hai.",
        "Rahu": "Jo kuch zyada hi aasaan lage use khud jaanchein, bharosa karke na chalein.",
        "Ketu": "Do hafte tak zor lagana band karein; yeh tab lautta hai jab aap peecha karna chhod dete hain.",
    },
    "te_en": {
        "Saturn": "Nemmadiga, dhruveekarinchagala panini modata cheyandi: anni rasi teesukondi, vaayida veyaboye gaduvu pooriti cheyandi.",
        "Mars": "Vedi taggincandi. Oka vaaram ee vishayamlo vaadinchakandi, itaru vaipu mundu kadalani ivvandi.",
        "Sun": "Nirnayam teesukogala vyakthini nerugaa kalavandi; ee pani kinda stayilo agipothundi.",
        "Moon": "Ee vaaram nirnayam teesukovaddu. Konni rojullo mee alochana maarutundi, kaabatti modata manasu sthimitapadani ivvandi.",
        "Mercury": "Anni rasi cheyandi, mundu pampinadanni malli chadavandi; tappuga artham chesukovadam padallo undi.",
        "Venus": "Malli adigeynu mundu sambandhanni sari cheyandi. Prajalu prathipadanaki kaadu, manishiki avunu antaru.",
        "Jupiter": "Mee tarapuna maatladamani oka seniorni adagandi; idi sifarasu dwara teruchukuntundi.",
        "Rahu": "Chaala sulabhamga kanipinchedi emaina unte meere swayamga parishilinchandi.",
        "Ketu": "Rendu vaarala paatu pravartinchadam aapandi; meeru venta padatam aapinappudu idi thirigi vastundi.",
    },
}


_WINDOW = {
    "en": None,       # the English sentence is written by timing_sentence
    "hi_en": ("Sabse kareeb samay {span} hai.", "Agla sambhavit avsar lagbhag {span} hai.",
              "Kundli is kaam ke liye koi saaf samay nahi dikhati."),
    "te_en": ("Sabse daggara samayam {span}.", "Tarvata avakasam sumaru {span}.",
              "Ee paniki kundali spashtamaina samayam chupinchadam ledu."),
}
_WAIT = {"en": "Plan the important move for the window above, not before it.",
         "hi_en": "Zaroori kadam upar bataye samay ke liye rakhein, usse pehle nahi.",
         "te_en": "Mukhyamaina nirnayam paina chepina samayaniki vaayida veyandi, antakumundu kaadu."}


def timing_line(timing: dict, plain: Any, lk: str) -> str:
    from llm.horary_judge import _SOON_DAYS, _format_window, timing_sentence
    if lk == "en":
        return str(getattr(plain, "timing", "") or "").strip() or timing_sentence(timing)
    near, later, none = _WINDOW[lk]
    if timing.get("beyond_horizon"):
        return none
    if not timing.get("window"):
        return ""
    span = _format_window(timing)
    return (near if int(timing.get("days_away", 999)) <= _SOON_DAYS else later).format(span=span)


def gloss(label: str, asks: str, lens_outlook: str, lk: str) -> str:
    table = _GLOSS_LOCAL[lk]
    if asks == "quantity":
        return table["quantity"]
    got = table.get(label, table["open"])
    return got[lens_outlook] if isinstance(got, dict) else got


def steps(plain: Any, ev: dict, timing: dict, label: str, lk: str) -> list[str]:
    out: list[str] = []
    remedy = str(getattr(plain, "remedy", "") or "").strip()
    if remedy and lk != "en":
        from llm.horary_judge import blocking_planet
        remedy = _REMEDY_LOCAL[lk].get(blocking_planet(ev), remedy)
    if remedy:
        out.append(remedy)
    if label in ("yes", "conditional") and timing.get("window") and not timing.get("beyond_horizon"):
        out.append(_WAIT[lk])
    try:
        from horary_answer import GENERAL_REMEDY, REMEDIES
        from llm.horary_judge import blocking_planet
        planet = blocking_planet(ev)
        mantra = str((REMEDIES.get(planet) or GENERAL_REMEDY).get("mantra") or "").strip()
        if mantra and remedy:
            out.append(mantra)
    except Exception:  # noqa: BLE001
        pass
    return out[:3]


# -------------------------------------------------------------------------- the page
def fact_rows(data: Optional[dict], ev: dict, lenses: dict[str, dict], asked: str) -> list[str]:
    data = data or {}
    rows: list[str] = []
    lagna = (data.get("lagna") or {}).get("sign") or ""
    moon = (data.get("planets") or {}).get("Moon") or {}
    head = f"Question moment: {asked}" if asked else "Question moment"
    if lagna:
        head += f"; rising sign {lagna}"
    if moon.get("sign"):
        head += f", Moon in {moon['sign']}"
    rows.append(head + ".")
    k = lenses.get("kp") or {}
    if k.get("bhava"):
        topic = str(ev.get("topic") or "").replace("_", " ").strip() or _HOUSE["en"].get(k["bhava"], "")
        rows.append(f"The matter is judged from the {QR._ord(k['bhava'])} house ({topic}).")
        if k.get("fav"):
            rows.append("Supporting areas: " + _meanings(k["fav"], "en", helps=True) + ".")
        if k.get("den"):
            rows.append("Opposing areas: " + _meanings(k["den"], "en") + ".")
    r = lenses.get("ruling") or {}
    if r.get("agree"):
        rows.append("Planets that decide the matter and also rule this moment: " + ", ".join(r["agree"]) + ".")
    m = lenses.get("moon") or {}
    if m:
        rows.append(f"Moon: {'waxing' if m['bright'] else 'waning'}"
                    + (f", in {m['nakshatra']}" if m.get("nakshatra") else "") + ".")
    if int(((data.get("radicality") or {}).get("score") or 0)) >= 3:
        rows.append("The moment looks like a casual or test question, so treat this answer with less weight.")
    return rows


def build(*, question: str, data: Optional[dict], evidence: dict, timing: Optional[dict],
          plain: Any, label: str, lang: str = "en", asked: str = "",
          asks: str = "") -> tuple[QR.QuestionReading, list[str], str]:
    """Returns (reading, fact rows, meta line) for ``QR.render_html``."""
    lk = QR._lang_key(lang)
    timing = timing or {}
    lenses = build_lenses(data, evidence, timing)
    answer = (str(getattr(plain, "answer", "") or "").strip() if lk == "en"
              else gloss(label, asks, outlook(lenses), lk))
    if label == "out_of_scope":
        return (QR.QuestionReading(stance="not_astrological", answer=answer, why=[], timing="", steps=[]),
                [], "")
    reading = QR.QuestionReading(
        stance=stance(label, lenses),
        answer=f"{answer} {because(lenses, lk)}".strip(),
        why=[lens_text(k, lenses[k], lk) for k in LENS_ORDER if k in lenses],
        timing=timing_line(timing, plain, lk),
        steps=steps(plain, evidence, timing, label, lk),
        lenses=[{"key": k, "vote": lenses[k]["vote"]} for k in LENS_ORDER if k in lenses],
        confidence=confidence(lenses, data))
    lagna = ((data or {}).get("lagna") or {}).get("sign") or ""
    moon = (((data or {}).get("planets") or {}).get("Moon") or {}).get("sign") or ""
    bits = [f"Asked {asked}" if asked else "", f"{lagna} rising" if lagna else "",
            f"Moon in {moon}" if moon else ""]
    meta_line = " &middot; ".join(html.escape(b) for b in bits if b)
    return reading, fact_rows(data, evidence, lenses, asked), meta_line


def label_of(judgement: Any, verdicts: Optional[dict]) -> str:
    """The judge's label, or the nearest one when only the reconciled verdict is known."""
    got = str(getattr(judgement, "label", "") or "")
    if got:
        return got
    v = str(((verdicts or {}).get("kp") or {}).get("verdict") or "").lower()
    return ("yes" if v == "yes" else "no" if v == "no" else "out_of_scope" if "out_of" in v
            else "conditional")
