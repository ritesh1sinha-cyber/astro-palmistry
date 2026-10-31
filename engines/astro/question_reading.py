"""A short, plain-language answer to ONE question the reader asked.

The older question report stacked every technique the engine owned (house
analysis, divisional charts, Lal Kitab, Chandra Naadi, transit lists, a dozen
remedies) under a verdict, so a simple "which gemstone suits me?" came back as
pages of unrelated lines. This module does the opposite:

1. ``build_fact_sheet`` keeps only what bears on the question: the house and
   lord that govern it, the natural indicator, the sign score, the running and
   next period, the transit of the two slow planets, and for gemstones the
   audited stone list. Lal Kitab and Chandra Naadi are left out on purpose.
2. A language model judges the question against that sheet and returns one
   small structured answer (verdict, short answer, a few reasons, timing,
   steps). Nothing it names is trusted until it passes ``_check``.
3. If the model is off, slow or fails the check, ``_fallback`` writes the same
   structure from the same facts, so the page never depends on the model.
4. ``render_html`` lays it out as one compact card.
"""
from __future__ import annotations

import html
import re
from datetime import date
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Stance = Literal["favourable", "mixed", "difficult", "not_astrological"]


class QuestionReading(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stance: Stance = Field(description="Overall outlook for what was asked.")
    answer: str = Field(description="Direct answer, 2-3 plain sentences, at most 60 words.")
    why: list[str] = Field(description="2-4 short reasons, each citing one chart fact that bears on the question.")
    timing: str = Field(description="One sentence on when, or empty if the question has no timing aspect.")
    steps: list[str] = Field(description="1-3 concrete things to do, at most 20 words each.")
    lenses: list[dict] = Field(default_factory=list,
                               description="[{key, vote}] for each lens that was judged; vote is +1, 0 or -1.")
    confidence: str = Field(default="", description="high / moderate / low, from how the lenses line up.")


_GOOD_DIGNITY = ("exalted", "moolatrikona", "own_sign", "friendly_sign")
_BAD_DIGNITY = ("debilitated", "enemy_sign")
_WEEKDAY = {"Sun": "Sunday", "Moon": "Monday", "Mars": "Tuesday", "Mercury": "Wednesday",
            "Jupiter": "Thursday", "Venus": "Friday", "Saturn": "Saturday",
            "Rahu": "Saturday", "Ketu": "Tuesday"}
# Questions where picking the moment for an action is meaningful advice.
_MOVE_DOMAINS = {"career_profession", "marriage_relationship", "children_progeny", "wealth_finances",
                 "property_assets", "foreign_relocation", "education_learning", "litigation_disputes"}
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


# --------------------------------------------------------------------------- facts
def _ord(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _and_join(items: list[str]) -> str:
    items = [str(i) for i in items if str(i)]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _month_year(iso: str) -> str:
    m = re.match(r"(\d{4})-(\d{2})", str(iso or ""))
    if not m:
        return str(iso or "")
    return f"{_MONTHS[int(m.group(2)) - 1]} {m.group(1)}"


def _pretty_window(text: str) -> str:
    """'Mercury Antardasha (2027-02-09 to 2029-06-14)' -> 'Mercury sub-period, Feb 2027 to Jun 2029'."""
    out = re.sub(r"\d{4}-\d{2}-\d{2}", lambda m: _month_year(m.group(0)), str(text or ""))
    out = out.replace("Antardasha", "sub-period").replace("Sub-Period", "sub-period")
    out = out.replace("Mahadasha", "main period")
    return re.sub(r"\s+", " ", out).strip(" ,")


def _planet_state(pc: dict, name: str) -> dict:
    from astro_precompute import get_dignity
    p = (pc.get("planets") or {}).get(name) or {}
    sign = p.get("sign", "")
    dig = p.get("dignity") or (get_dignity(name, sign) if sign else "unknown")
    house = int(p.get("house") or 0)
    return {"planet": name, "sign": sign, "house": house, "dignity": str(dig),
            "retro": bool(p.get("retrograde")), "combust": bool(p.get("combust")),
            "hard_house": house in (6, 8, 12)}


def _dignity_words(dig: str) -> str:
    d = str(dig or "")
    if d == "exalted":
        return "exalted (at its strongest)"
    if d in ("own_sign", "moolatrikona"):
        return "in its own sign (strong)"
    if d == "friendly_sign":
        return "in a friendly sign"
    if d == "debilitated":
        return "debilitated (weak)"
    if d == "enemy_sign":
        return "in an unfriendly sign"
    return ""


def _periods(pc: dict) -> dict:
    vim = pc.get("vimshottari") or {}
    md = vim.get("current_md") or {}
    ad = next((a for a in (vim.get("current_md_antardashas") or []) if a.get("status") == "current"), {})
    return {
        "main": md.get("md_lord", ""),
        "main_until": _month_year(md.get("end", "")),
        "sub": ad.get("ad_lord", ""),
        "sub_from": _month_year(ad.get("start", "")),
        "sub_until": _month_year(ad.get("end", "")),
    }


def _slow_transits(conf: Any) -> str:
    """Jupiter and Saturn only, in a sentence; the full transit list is noise here."""
    parts = re.findall(r"Transit (Jupiter|Saturn) in House (\d+) \((\w+)", conf.transit_finding or "")
    return "; ".join(f"{p} is crossing your {_ord(int(h))} house ({s})" for p, h, s in parts)


def build_fact_sheet(conf: Any, pc: dict, cfg: dict) -> dict:
    """Only the facts that can bear on the question. No Lal Kitab, no Chandra Naadi."""
    from confluence_question_engine import audit_chart_gemstones
    facts: dict[str, Any] = {
        "question": conf.question,
        "domain_key": conf.domain_key,
        "domain": cfg.get("title", conf.domain_title),
        "lagna": conf.lagna,
        "lagna_lord": conf.lagna_lord,
        "moon_sign": conf.moon_sign,
    }
    house = int(conf.primary_house)
    lord = _planet_state(pc, conf.primary_house_lord)
    karakas = [_planet_state(pc, k) for k in (cfg.get("karakas") or [])[:2]]
    sav = re.search(r"holds (\d+)", conf.ashtakavarga_finding or "")
    sav_n = int(sav.group(1)) if sav else 0
    facts["house"] = {"number": house, "sign": conf.primary_house_sign, "sav": sav_n, "lord": lord}
    facts["karakas"] = karakas
    facts["periods"] = _periods(pc)
    facts["next_window"] = _pretty_window(conf.breakthrough_period)
    facts["transits"] = _slow_transits(conf)
    facts["transit_parts"] = re.findall(r"Transit (Jupiter|Saturn) in House (\d+) \((\w+)",
                                        conf.transit_finding or "")

    signals_for, signals_against = [], []
    if conf.domain_key not in ("gemstones_remedies", "out_of_domain"):
        (signals_against if lord["hard_house"] else signals_for).append("ruling planet placement")
        if lord["dignity"] in _GOOD_DIGNITY:
            signals_for.append("ruling planet dignity")
        elif lord["dignity"] in _BAD_DIGNITY:
            signals_against.append("ruling planet dignity")
        if karakas:
            k = karakas[0]
            bad = k["hard_house"] or k["dignity"] in _BAD_DIGNITY or k["combust"]
            (signals_against if bad else signals_for).append("natural indicator")
        if sav_n:
            (signals_for if sav_n >= 28 else signals_against).append("sign score")
    facts["signals_for"], facts["signals_against"] = signals_for, signals_against
    import question_lenses as _QL
    _owned = _QL.owned_houses(conf.lagna)
    facts["placements"] = {
        p: {"house": int(d.get("house") or 0), "owns": _owned.get(p, [])}
        for p, d in (pc.get("planets") or {}).items() if int(d.get("house") or 0)}
    facts["lenses"] = {}
    if conf.domain_key not in ("gemstones_remedies", "out_of_domain"):
        import question_lenses as QL
        facts["lenses"] = QL.build_lenses(conf, pc, cfg, facts)

    if conf.domain_key == "gemstones_remedies":
        audit = (audit_chart_gemstones(pc) or {}).get("audit", {})
        rec, avoid = [], []
        for planet, inf in audit.items():
            row = {"planet": planet, "gem": inf["gem"], "metal": inf["metal"],
                   "finger": inf["finger"], "day": inf["day"], "mantra": inf["mantra"],
                   "houses": inf.get("owned_houses", []), "in_house": inf.get("house")}
            if inf["status"] == "RECOMMENDED":
                rec.append(row)
            elif inf["status"] in ("AVOID", "STRICTLY_AVOID"):
                row["reason"] = _short_avoid_reason(inf)
                avoid.append(row)
        asked = []
        for planet in asked_planets(conf.question):
            inf = audit.get(planet)
            if not inf:
                continue
            verdict = ("wear" if inf["status"] == "RECOMMENDED"
                       else "avoid" if inf["status"] in ("AVOID", "STRICTLY_AVOID") else "mantra")
            asked.append({"planet": planet, "gem": inf["gem"], "metal": inf["metal"], "finger": inf["finger"],
                          "day": inf["day"], "mantra": inf["mantra"], "houses": inf.get("owned_houses", []),
                          "in_house": inf.get("house"), "verdict": verdict,
                          "reason": _short_avoid_reason(inf) if verdict == "avoid" else ""})
        facts["gems"] = {"recommended": rec, "avoid": avoid, "asked": asked}
    return facts


# A stone the question names is answered first, whatever the audit ranked it.
_STONE_WORDS = (
    ("Saturn", r"blue\s+sapphire|neelam|nilam|neelam"),
    ("Jupiter", r"yellow\s+sapphire|pukhraj|pukhraaj|pukhraj"),
    ("Venus", r"diamond|heera|hira|white\s+zircon|zircon"),
    ("Mercury", r"emerald|panna"),
    ("Mars", r"red\s+coral|coral|moonga|munga"),
    ("Moon", r"pearl|moti"),
    ("Sun", r"ruby|manik|manikya"),
    ("Rahu", r"hessonite|gomed|gomedh"),
    ("Ketu", r"cat'?s?\s*eye|lehsunia|lahsunia"),
)


def asked_planets(question: str) -> list[str]:
    """Planets whose stone the question names ('sapphire' alone means both sapphires)."""
    low = str(question or "").lower()
    out = [p for p, pat in _STONE_WORDS if re.search(rf"\b(?:{pat})\b", low)]
    if re.search(r"\bsapphires?\b", low) and not ({"Saturn", "Jupiter"} & set(out)):
        out += ["Saturn", "Jupiter"]
    return out


def _short_avoid_reason(inf: dict) -> str:
    text = " ".join(inf.get("reasons") or [])
    if "8th house" in text and "placed in the 8th" in text:
        return "its planet sits in your 8th house, which stirs up sudden trouble"
    if "Dusthana" in text:
        return "its planet rules a difficult house (6th, 8th or 12th) and could magnify those problems"
    if "Kendradhipati" in text or "Maraka" in text:
        return "its planet rules a house of loss or obstruction for your rising sign"
    return "it is not a safe stone for your chart"


def _stance_hint(facts: dict) -> str:
    n_for, n_against = len(facts["signals_for"]), len(facts["signals_against"])
    if facts["domain_key"] == "gemstones_remedies":
        asked = facts["gems"].get("asked") or []
        if asked:           # the named stone decides the outlook, not the rest of the list
            return "favourable" if asked[0]["verdict"] == "wear" else "difficult"
        return "favourable" if facts["gems"]["recommended"] else "mixed"
    if facts["domain_key"] == "out_of_domain":
        return "not_astrological"
    if facts.get("lenses"):
        # The badge must agree with the sentence the reader sees, and that sentence is chosen from the
        # same (birth promise, running now) pair.
        p, n = _verdict_key(facts)
        if p > 0 and n > 0:
            return "favourable"
        if p < 0:
            return "difficult"
        return "mixed"
    if n_for - n_against >= 2:
        return "favourable"
    if n_against - n_for >= 2:
        return "difficult"
    return "mixed"


# ------------------------------------------------------------------------- findings
def _state_words(k: dict) -> str:
    bits = []
    if k["hard_house"]:
        bits.append("in a hard house")
    if k["dignity"] in _BAD_DIGNITY:
        bits.append("weak")
    if k["combust"]:
        bits.append("too close to the Sun")
    return "under strain (" + ", ".join(bits) + ")" if bits else "well placed"


def _findings(facts: dict, lang: str = "en") -> list[tuple[str, str]]:
    """Plain, already-true sentences. The model may choose among them; it may not add to them."""
    return [(fid, text) for fid, _lens, text in _findings_full(facts, lang)]


def _lens_findings(facts: dict, lang: str, start: int) -> list[tuple[str, str, str]]:
    """One sentence per live lens (Vimshottari, Jaimini, Yogini, transit, Chandra Naadi)."""
    import question_lenses as QL
    lk = _lang_key(lang)
    rows = []
    for key in QL.LENS_ORDER[1:]:
        d = (facts.get("lenses") or {}).get(key)
        if not d:
            continue
        if lk == "en":
            text = QL.text_en(key, d, facts)
        else:
            import question_reading_i18n as I18N
            text = I18N.lens_text(key, d, facts, lk)
        if text:
            rows.append((f"F{start + len(rows)}", key, text))
    return rows


def _findings_full(facts: dict, lang: str = "en") -> list[tuple[str, str, str]]:
    """(id, lens, sentence). Birth-promise sentences first, then one per live lens."""
    if facts["domain_key"] in ("gemstones_remedies", "out_of_domain"):
        return []
    if _lang_key(lang) != "en":
        import question_reading_i18n as I18N
        promise = I18N.findings(facts, _lang_key(lang))
    else:
        promise = _promise_findings(facts)
    rows = [(fid, "promise", text) for fid, text in promise]
    return rows + _lens_findings(facts, lang, len(rows) + 1)


def _promise_findings(facts: dict) -> list[tuple[str, str]]:
    h = facts["house"]
    lord = h["lord"]
    dw = _dignity_words(lord["dignity"])
    rows: list[tuple[str, str]] = [(
        "F1",
        f"{lord['planet']} rules your {_ord(h['number'])} house, which governs this. It sits in house "
        f"{lord['house']} in {lord['sign']}" + (f" and is {dw}" if dw else "")
        + (" - a hard house that brings delay." if lord["hard_house"]
           else " - a weak placement, even though the house itself is helpful."
           if lord["dignity"] in _BAD_DIGNITY else " - a supportive placement."))]
    for k in facts["karakas"]:
        if k["planet"] == lord["planet"]:
            continue                      # already said in F1
        rows.append((f"F{len(rows) + 1}", f"{k['planet']}, a natural indicator for this, is in house "
                                          f"{k['house']} ({k['sign']}) and is {_state_words(k)}."))
    nxt = len(rows) + 1
    if h["sav"]:
        rows.append((f"F{nxt}", f"The {_ord(h['number'])} house scores {h['sav']} "
                                f"({'above' if h['sav'] >= 28 else 'below'} the average of 28)."))
        nxt += 1
    return rows          # the running period and the transits are judged by their own lenses


def _timing_line(facts: dict, lang: str = "en") -> str:
    if _lang_key(lang) != "en":
        import question_reading_i18n as I18N
        return I18N.timing(facts, _lang_key(lang))
    vuln = (facts.get("lenses") or {}).get("vulnerability")
    if vuln:                  # health: the useful window is when to take more care, not a "best" period
        import question_health as QH
        return QH.watch_line(vuln, "en")
    w = facts.get("next_window") or ""
    return f"The period that supports this most is {w}." if w else ""


_WHEN_WORDS = re.compile(r"\b(when|how long|by when|which year|what year|how soon|kab|eppudu|date|timing|time)\b", re.I)


def _wants_timing(facts: dict, flag: Optional[bool] = None) -> bool:
    if facts["domain_key"] in ("gemstones_remedies", "out_of_domain"):
        return False
    # A present-tense relationship check does not need a marriage-style future window.
    question = facts["question"]
    if (re.search(r"\b(right now|currently|current|at present)\b", question, re.I)
            and not _WHEN_WORDS.search(question)):
        return False
    vuln = (facts.get("lenses") or {}).get("vulnerability") or {}
    if (vuln.get("watch") or {}).get("range") or (vuln.get("now") or {}).get("range"):
        return True
    return bool(_WHEN_WORDS.search(question)) or facts["domain_key"] in _MOVE_DOMAINS


_MANTRA = {
    "Sun": "Om Suryaya Namah", "Moon": "Om Chandraya Namah", "Mars": "Om Mangalaya Namah",
    "Mercury": "Om Budhaya Namah", "Jupiter": "Om Gurave Namah", "Venus": "Om Shukraya Namah",
    "Saturn": "Om Shanaischaraya Namah", "Rahu": "Om Rahave Namah", "Ketu": "Om Ketave Namah",
}


def _gem_wear_step(r: dict) -> str:
    return (f"Try {r['gem']} for three days before regular wear. If comfortable, use {r['metal'].lower()} on the "
            f"{r['finger'].lower()}, on a {r['day']} morning in the bright half of the month.")


def _practical_step(facts: dict, has_window: bool) -> str:
    key = facts["domain_key"]
    q = facts["question"].lower()
    window = "the period named above"
    if key == "career_profession":
        if "promot" in q:
            return (f"Document your results now; use {window} to request a promotion discussion." if has_window
                    else "Document your results and have a specific promotion conversation with your manager.")
        if re.search(r"first\s+job|unemployed", q):
            return (f"Build a focused CV and practise interviews; use {window} for applications and interviews."
                    if has_window else "Build a focused CV, practise interviews and apply consistently.")
        if re.search(r"business|startup|self\s*-?\s*employ", q):
            return (f"Validate demand, prepare a budget and keep a cash cushion; use {window} for a measured launch."
                    if has_window else "Validate demand, prepare a budget and keep a cash cushion before launching.")
        if "retir" in q:
            return (f"Review pension, monthly expenses and health cover; use {window} for transition planning."
                    if has_window else "Review pension, monthly expenses and health cover before setting a retirement date.")
        if re.search(r"what\s+career|which\s+career|career\s+(?:should|direction)|choose.*career", q):
            return ("Compare a few career paths against your interests and strengths, then try a small project "
                    "or speak with a mentor.")
        if re.search(r"change|switch|new job|another job", q):
            return (f"Update your CV and compare written offers; use {window} for applications or a switch."
                    if has_window else "Update your CV and compare written offers before resigning.")
        if re.search(r"secure|security|safe|layoff|fired|demotion", q):
            return "Keep your skills current, document your work and maintain a cash cushion."
        return "Document your work and discuss the next concrete career step with your manager."
    if key == "marriage_relationship":
        if re.search(r"marri|wedding|shaadi|vivah", q):
            return (f"Use {window} for introductions or family discussions, without rushing a commitment."
                    if has_window else "Discuss expectations openly with family and avoid rushing a commitment.")
        return "Have one calm conversation about expectations and avoid decisions during an argument."
    if key == "children_progeny":
        return (f"Use {window} for family planning; discuss any medical concerns with a qualified clinician."
                if has_window else "Keep preparation and health first; discuss medical concerns with a qualified clinician.")
    if key == "foreign_relocation":
        return (f"Prepare documents and funds now; use {window} for visa applications or confirmed travel."
                if has_window else "Prepare your documents and funds before making travel or relocation commitments.")
    if key == "wealth_finances":
        return (f"Automate savings and review debt before using {window} for major financial commitments."
                if has_window else "Automate savings, review debt and avoid rushed financial commitments.")
    if key == "education_learning":
        return (f"Prepare early; use {window} for exams, applications or important submissions." if has_window
                else "Use a steady study schedule and practise under exam conditions.")
    if key == "property_assets":
        if re.search(r"sell|sale", q):
            return (f"Verify title, ownership and sale documents; use {window} for serious buyer discussions."
                    if has_window else "Verify title, ownership and sale documents before accepting an offer.")
        if re.search(r"transfer|gift", q):
            return ("Review ownership, tax and family implications with a qualified professional before "
                    "transferring the property.")
        return (f"Verify title, loan terms and documents; use {window} for serious property steps." if has_window
                else "Verify the title, loan terms and documents before committing to a property.")
    if key == "litigation_disputes":
        if "custody" in q:
            return ("Keep child-focused records, follow your family lawyer's advice and avoid involving the "
                    "child in conflict.")
        if "divorce" in q:
            return (f"Organise case and financial records; use {window} for lawyer-guided settlement discussions."
                    if has_window else "Organise case and financial records and follow your family lawyer's advice.")
        if re.search(r"property|inheritance|tenant|ownership", q):
            return (f"Organise ownership, payment and communication records; use {window} for lawyer-guided mediation."
                    if has_window else "Organise ownership, payment and communication records and follow your lawyer's advice.")
        return (f"Prepare documents and follow your lawyer's advice; use {window} for settlement discussions."
                if has_window else "Prepare your documents and follow your lawyer's advice before deciding on settlement.")
    if key == "speech_neurology":
        return "Work with a qualified speech or medical professional on a consistent support plan."
    if key == "general_destiny":
        return "Choose one practical priority and review your progress monthly."
    return ""


def _steps(facts: dict, lang: str = "en") -> list[str]:
    if _lang_key(lang) != "en":
        import question_reading_i18n as I18N
        return I18N.steps(facts, _lang_key(lang))
    key = facts["domain_key"]
    if key == "gemstones_remedies":
        rec = facts["gems"]["recommended"]
        asked = facts["gems"].get("asked") or []
        if asked:
            out = []
            for r in asked:
                if r["verdict"] == "wear":
                    out.append(_gem_wear_step(r))
                else:
                    out.append(f"Skip {r['gem']}; chant {r['planet']}'s mantra and give a small donation on "
                               f"{_WEEKDAY.get(r['planet'], 'its day')}s.")
            skip = {r["planet"] for r in asked}
            for r in [x for x in rec if x["planet"] not in skip][:1]:
                out.append("If you want another stone, " + _gem_wear_step(r)[0].lower() + _gem_wear_step(r)[1:])
            return out[:3]
        steps = [_gem_wear_step(r) for r in rec[:3]]
        if facts["gems"]["avoid"] and len(steps) < 3:
            steps.append("Skip the stones listed as avoid; use that planet's mantra and a small donation instead.")
        if not steps:
            lord = facts["lagna_lord"]
            steps.append(f"Chant {lord}'s mantra on {_WEEKDAY.get(lord, 'its day')}s and give a small donation.")
        return steps[:3]
    if key == "out_of_domain":
        return []
    steps = []
    cands = [facts["house"]["lord"], *facts["karakas"]]
    weak = next((c for c in cands if c["hard_house"] or c["dignity"] in _BAD_DIGNITY or c["combust"]), None)
    target = weak or (facts["karakas"][0] if facts["karakas"] else None)
    if target:
        k = target["planet"]
        role = ("rules the house behind this question" if target is facts["house"]["lord"]
                else "is a natural indicator for this question")
        if target["hard_house"]:
            state = " and sits in a hard house in your chart"
        elif target["dignity"] in _BAD_DIGNITY:
            state = " and is weak in your chart"
        elif target["combust"]:
            state = " and is overpowered by the Sun in your chart"
        else:
            state = ""
        steps.append(f"{k} {role}{state}, so it is the planet to support: chant {_MANTRA.get(k, 'its mantra')} "
                     f"108 times on {_WEEKDAY.get(k, 'its day')}s and offer a small donation.")
    vuln = (facts.get("lenses") or {}).get("vulnerability")
    if vuln:
        import question_health as QH
        step = QH.prevent_step(vuln, "en")
        if step and QH.sanitized(step):
            steps.append(step)
    practical = _practical_step(facts, bool(facts.get("next_window") and _wants_timing(facts)))
    if practical:
        steps.append(practical)
    return steps[:3]


def _gem_why(facts: dict, lang: str = "en") -> list[str]:
    if _lang_key(lang) != "en":
        import question_reading_i18n as I18N
        return I18N.gem_why(facts, _lang_key(lang))
    why = [_asked_why(r) for r in facts["gems"].get("asked", [])]
    asked_planets_ = {r["planet"] for r in facts["gems"].get("asked", [])}
    for r in facts["gems"]["recommended"]:
        if r["planet"] in asked_planets_:
            continue
        hs = _and_join([_ord(int(h)) for h in r["houses"]])
        why.append(f"{r['planet']} rules your {hs} house{'s' if len(r['houses']) > 1 else ''}, "
                   f"which makes {r['gem']} a supportive stone for you.")
    for r in facts["gems"]["avoid"][:2]:
        if r["planet"] in asked_planets_:
            continue
        why.append(f"{r['gem']} is best avoided because {r['reason']}.")
    return why[:5 if facts["gems"].get("asked") else 4]


def _place_phrase(r: dict) -> str:
    """'Saturn rules your 8th and 9th houses and sits in house 6'."""
    hs = _and_join([_ord(int(h)) for h in r["houses"]])
    rules = (f"{r['planet']} rules your {hs} house{'s' if len(r['houses']) > 1 else ''}" if r["houses"]
             else f"{r['planet']} rules no house of its own for your rising sign")
    return rules + (f" and sits in house {r['in_house']}" if r.get("in_house") else "")


def _asked_why(r: dict) -> str:
    """Why the stone the reader asked about is, or is not, for them."""
    if r["verdict"] == "wear":
        return f"{_place_phrase(r)}, which makes {r['gem']} a supportive stone for you."
    if r["verdict"] == "avoid":
        return f"{r['gem']} is best avoided because {r['reason']} ({_place_phrase(r)})."
    return (f"{_place_phrase(r)}. For your rising sign that is not a planet whose stone is safe to wear, "
            f"so mantra and charity suit it better.")


def _asked_answer(facts: dict) -> str:
    """Direct answer about the named stone, then the stones that do suit the reader."""
    parts = []
    for r in facts["gems"]["asked"]:
        parts.append({"wear": f"{r['gem']} suits you.",
                      "avoid": f"{r['gem']} is not advised for you.",
                      "mantra": f"{r['gem']} is not advised for you; {r['planet']}'s mantra and charity suit "
                                f"better."}[r["verdict"]])
    skip = {r["planet"] for r in facts["gems"]["asked"]}
    others = [r["gem"] for r in facts["gems"]["recommended"] if r["planet"] not in skip]
    if others and not all(r["verdict"] == "wear" for r in facts["gems"]["asked"]):
        parts.append(f"The stones that do suit you are {_and_join(others)}.")
    return " ".join(parts)


# ------------------------------------------------------------------------- the model
class QuestionJudgement(BaseModel):
    """What the model decides. It never writes a fact: reasons are picked by id."""
    model_config = ConfigDict(extra="forbid")

    stance: Stance
    answer: str = Field(description="ONE sentence, under 18 words, that directly answers the question asked, "
                                    "addressing the reader with 'your' or 'you'.")
    because: str = Field(default="", description="ONE sentence, under 24 words, using 'your': a concrete "
                                                 "plain-language reason for this life area, drawn from the findings.")
    use: list[str] = Field(description="Ids (F1, F2...) of the 3-5 findings that matter for THIS question.")
    needs_timing: bool = Field(description="True only if the question asks when / how long / which year.")


_SYSTEM = (
    "You are an experienced Vedic astrologer answering ONE question for one person. First work out "
    "what the question is really asking. Judge the underlying chart pattern against current conditions "
    "using every numbered finding. Fill `answer` with one short sentence that directly answers the "
    "question in plain, hedged words. Say it the way a kind person would say it aloud, using the "
    "question's OWN subject (changing jobs, getting married, repaying the loan, studying abroad) rather than "
    "a generic phrase like 'your prospects'. Examples of the shape, not the words: 'A move to a new "
    "role looks possible, though you may need patience and a clear plan.' / 'Marriage looks possible, though "
    "it may come later than you hope.' / 'Clearing the loan looks manageable if you keep your expenses tight.' "
    "For a 'should I' question, say how well the chart supports the move ('the chart gives a change of job "
    "some support, though it asks for a clear plan'), never 'you should' or 'you will'. "
    "The two sentences together MUST contain the literal word 'you' or 'your'. Fill `because` with one sentence giving the "
    "concrete reason in everyday language, taken from the PLAIN FACTS. The `because` sentence must add a "
    "concrete reason for THIS life area, not restate the answer or merely say 'underlying pattern' or "
    "'current conditions'. Never name a planet or a sign, and never use the words "
    "birth promise, running period, sub-period, Chara, Yogini, Chandra Naadi, lens, confluence, house, planet, "
    "planetary, placement, dasha or transit in the customer text. Do not say "
    "will, soon, eventually, certainly or definitely, and never tell the reader to make a major life "
    "decision. Use ONLY the numbered findings supplied; never add a position, date or gemstone that "
    "is not written there. In `use` list the ids of the 3-5 findings that genuinely matter for THIS "
    "question, covering both the underlying pattern and current conditions; leave out the rest. No "
    "headings, padding or repetition of the question. stance is favourable, mixed or difficult; stay "
    "close to the suggested stance unless a finding clearly says otherwise. Set needs_timing true only "
    "when the question asks about time. Never put a date, year or period length in the text: timing "
    "is shown separately."
)

_LANG_NOTE = {
    "hi_en": "Write the answer in natural Hindi using English letters (Roman Hindi), not Devanagari.",
    "te_en": "Write the answer in natural Telugu using English letters (Roman Telugu), not Telugu script.",
}


def _lang_key(lang: str) -> str:
    low = str(lang or "").lower().strip()
    if low in ("hi_en", "hinglish", "hi", "hindi"):
        return "hi_en"
    if low in ("te_en", "tenglish", "te", "telugu"):
        return "te_en"
    return "en"


def _prompt(facts: dict) -> str:
    lines = [f"QUESTION: {facts['question']}",
             f"AREA: {facts['domain']}",
             f"Rising sign: {facts['lagna']}. Moon sign: {facts['moon_sign']}.",
             f"Suggested stance: {_stance_hint(facts)}.",
             "FINDINGS:"]
    if "gems" in facts:
        for r in facts["gems"]["recommended"]:
            lines.append(f"- SUITS: {r['gem']} ({r['planet']} rules your "
                         f"{_and_join([_ord(int(h)) for h in r['houses']])} houses).")
        for r in facts["gems"]["avoid"]:
            lines.append(f"- AVOID: {r['gem']} because {r['reason']}.")
        asked = facts["gems"].get("asked") or []
        if asked:
            for r in asked:
                verdict = {"wear": "it SUITS the reader", "avoid": "the reader should AVOID it",
                           "mantra": "it is NOT ADVISED to wear; mantra and charity instead"}[r["verdict"]]
                lines.append(f"- ASKED STONE: {r['gem']}: {verdict}. {_place_phrase(r)}.")
            lines.append("`answer` MUST be one plain sentence that says whether the ASKED STONE suits the "
                         "reader, naming that stone, exactly as the audit says. `because` gives the reason "
                         "from its line and may name the stones that do suit the reader.")
        else:
            lines.append("`answer` MUST name every SUITS stone and every AVOID stone, in that order. "
                         "`because` gives the reason in plain words from the SUITS and AVOID lines only; "
                         "do not talk about a 'birth promise' or periods here.")
    else:
        lens_labels = {"promise": "birth promise", "vimshottari": "running period", "jaimini": "Chara period",
                       "yogini": "Yogini", "transit": "transit", "naadi": "Chandra Naadi",
                       "vulnerability": "body vulnerability"}
        votes = facts.get("lenses") or {}
        if "vulnerability" in votes:
            lines.insert(4, "HEALTH QUESTION (extra care is "
                            + ("ADVISED right now: the running period, Chandra Naadi or the current sub-period "
                               "shows strain" if _care_now(facts) else "not specially needed right now")
                            + "): `answer` must say how the health outlook looks AND name the body "
                            "areas that need care, using the body vulnerability finding (Chandra Naadi and the "
                            "disease pattern). `because` is ONE short sentence saying whether the running "
                            "period makes now a time for extra care; do not repeat the body areas and do not "
                            "list lens or period names. Speak of "
                            "sensitivity and care only: never name an illness, never predict illness, "
                            "accident, surgery or lifespan.")
        if votes:
            word = {1: "supports", 0: "neutral", -1: "strains"}
            lines.insert(4, "How the lenses line up: " + "; ".join(
                f"{lens_labels[k]} {word[votes[k]['vote']]}" for k in lens_labels if k in votes) + ".")
        if votes:
            p, n = _verdict_key(facts)
            lines.insert(5, "Judgement guide (answer the question FIRST, then give one concrete reason): the underlying "
                         f"pattern is { {1: 'supportive', 0: 'mixed', -1: 'strained'}[p] }; current conditions are "
                         f"{ {1: 'helpful', 0: 'mixed', -1: 'demanding'}[n] }. Do not copy these labels into the answer.")
        try:
            plain = plain_reasons(facts, "en")
        except Exception:                                              # noqa: BLE001
            plain = []
        # The visible reasons name the running planet ("the current Sun phase"); the answer must not.
        plain = [re.sub(r"\bcurrent (?:" + "|".join(_PLANETS) + r") phase", "current phase", t) for t in plain]
        if plain:
            lines.insert(4, "PLAIN FACTS (put the answer and reason in these everyday words; they are safe to "
                            "paraphrase): " + " ".join(plain))
        for fid, lens, text in _findings_full(facts):
            lines.append(f"{fid} [{lens_labels.get(lens, lens)}]: {text}")
        lines.append("The numbered findings are technical background for choosing `use`; do not copy their "
                     "wording or any planet name into `answer` or `because`.")
    return "\n".join(lines)


def _care_now(facts: dict) -> bool:
    """Health: does the live picture ask for extra care? (running period, Chandra Naadi, current sensitive period)"""
    lenses = facts.get("lenses") or {}
    vuln = lenses.get("vulnerability") or {}
    return bool((lenses.get("vimshottari") or {}).get("vote", 0) < 0
                or (lenses.get("naadi") or {}).get("vote", 0) < 0
                or (lenses.get("naadi") or {}).get("cautions")
                or vuln.get("current_hard"))


_GEM_NAMES = ("ruby", "pearl", "red coral", "coral", "emerald", "yellow sapphire", "blue sapphire",
              "diamond", "white zircon", "hessonite", "gomed", "cat's eye", "cats eye")
_PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")
_CLAIM = re.compile(
    r"\b(Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu)\b[^.;]{0,60}?"
    r"(?:\bhouse\s*(\d{1,2})\b|\b(\d{1,2})(?:st|nd|rd|th)\s+house\b)")


def _true_claims(facts: dict) -> set[tuple[str, int]]:
    """(planet, house) pairs the fact sheet supports: placements, rulerships and slow transits."""
    ok: set[tuple[str, int]] = set()
    h = facts["house"]
    lord = h["lord"]
    ok |= {(lord["planet"], lord["house"]), (lord["planet"], h["number"])}
    for k in facts["karakas"]:
        ok.add((k["planet"], k["house"]))
    for p, n in re.findall(r"(Jupiter|Saturn) is crossing your (\d+)", facts.get("transits") or ""):
        ok.add((p, int(n)))
    for p, n, _s in facts.get("transit_parts") or []:
        ok.add((p, int(n)))
    # Every natal placement and rulership is a true fact the answer may cite.
    for p, d in (facts.get("placements") or {}).items():
        ok.add((p, int(d["house"])))
        ok.update((p, int(x)) for x in d.get("owns", []))
    for r in (facts.get("gems") or {}).get("recommended", []) + (facts.get("gems") or {}).get("avoid", []):
        ok.update({(r["planet"], int(x)) for x in r["houses"]})
        if r.get("in_house"):
            ok.add((r["planet"], int(r["in_house"])))
    return ok


def _check(ans: str, facts: dict) -> list[str]:
    from llm.validate import enforce_user_voice
    problems = list(enforce_user_voice(ans))
    if not ans.strip():
        problems.append("answer is empty")
    if len(ans.split()) > 60:
        problems.append("answer is longer than 60 words")
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", ans.strip()) if s.strip()]
    if len(sentences) >= 2:
        def trigrams(text: str) -> set[tuple[str, ...]]:
            words = re.findall(r"[a-z]+", text.lower())
            return set(zip(words, words[1:], words[2:]))
        if trigrams(sentences[0]) & trigrams(sentences[1]):
            problems.append("the reason repeats the answer instead of adding information")
    if re.search(r"lal\s*kitab|python|code|```", ans, re.I):
        problems.append("answer contains something that is not part of a chart answer")
    if re.search(r"\b20\d\d\b", ans):
        problems.append("puts a year in the answer; timing is shown separately")
    if re.search(r"\b(will|definitely|certainly|guaranteed|inevitable|destined|sure\s+to)\b", ans, re.I):
        problems.append("uses certainty instead of a hedged chart reading")
    if re.search(r"\b(soon|eventually|any\s+time\s+now|around\s+the\s+corner)\b", ans, re.I):
        problems.append("adds vague timing that the fact sheet does not establish")
    if re.search(r"\byou\s+(?:should|must|ought\s+to)\s+(?:\w+\s+){0,3}"
                 r"(?:chang\w*|quit|leave|marry|divorce|separate|buy|sell|invest|move|relocate|settle|travel|proceed)\b",
                 ans, re.I):
        problems.append("tells the reader to make a major life decision instead of explaining the outlook")
    if "gems" not in facts and re.search(
            r"\b(birth\s+promise|underlying\s+pattern|current\s+conditions|running\s+period|main\s+period|"
            r"sub-period|chara|yogini|chandra\s+naadi|body\s+vulnerability|lenses?|confluence|mahadasha|"
            r"antardasha|dashas?|transits?|planets?|planetary|placements?|exalted|debilitated|moolatrikona|"
            r"sun|moon|mars|mercury|jupiter|venus|saturn|rahu|ketu|"
            r"house\s*\d{1,2}|\d{1,2}(?:st|nd|rd|th)\s+house)\b", ans, re.I):
        problems.append("uses chart-technique or report language instead of a plain explanation")
    if "gems" in facts and re.search(
            r"\b(?:rules?\s+your|sits?\s+in|placed\s+in|houses?\s*\d{1,2}|"
            r"\d{1,2}(?:st|nd|rd|th)\s+houses?)\b", ans, re.I):
        problems.append("uses technical gemstone reasoning instead of a plain explanation")
    if facts.get("domain_key") != "career_profession" and re.search(
            r"\b(?:career\s+base|career\s+prospects|job\s+security|promotion\s+prospects)\b", ans, re.I):
        problems.append("answers about career instead of the life area asked")
    try:                      # the page's last filter deletes whole sentences it dislikes: never ship one
        from qa_checks.customer_text_sanitizer import _internal_leak
        if _internal_leak(ans):
            problems.append("contains a phrase the customer page filter would delete; reword it plainly")
    except Exception:  # noqa: BLE001
        pass
    if "vulnerability" in (facts.get("lenses") or {}):
        if re.search(r"\b(cancer|diabet\w*|tumou?rs?|disease|illness(?:es)?|surgery|operation|accident|fatal|"
                     r"die|dies|dying|death|terminal|lifespan|longevity)\b", ans, re.I):
            problems.append("names an illness or predicts harm; speak of sensitivity and care only")
        if not re.search(r"\b(health|body|wellbeing|well-being|vitality|energy|care|routine|check-?ups?|"
                         r"strain|sensitiv\w*)\b", ans, re.I):
            problems.append("does not say how the health outlook looks")
        if _care_now(facts) and re.search(r"\b(does not|doesn't|do not|no need|not need|nothing)\b[^.]{0,60}"
                                          r"\b(care|caution|attention)\b", ans, re.I):
            problems.append("says no extra care is needed now, but the chart shows strain right now")
    if facts.get("lenses"):
        p, _n = _verdict_key(facts)
        for sent in re.split(r"(?<=[.!?])\s", ans):
            if not re.search(r"\b(birth )?(promise|promises)\b", sent, re.I):
                continue
            hedged = re.search(r"\b(but|though|however|yet|while|although)\b", sent, re.I)
            good = re.search(r"\b(strong|supports?|supportive|good|favou?rable|promising|encouraging)\b", sent, re.I)
            bad = re.search(r"\b(weak|delays?|delayed|poor|limited|difficult|hard|strain|debilitated)\b", sent, re.I)
            if p < 0 and good and not bad and not hedged:
                problems.append("calls the birth promise good, but the chart's birth promise is weak")
                break
            if p > 0 and bad and not good and not hedged:
                problems.append("calls the birth promise weak, but the chart's birth promise is strong")
                break
    true = _true_claims(facts)
    for m in _CLAIM.finditer(ans):
        house = int(m.group(2) or m.group(3))
        if (m.group(1), house) not in true:
            problems.append(f"says {m.group(1)} is tied to house {house}, which the findings do not say")
            break
    if "gems" not in facts:
        low = ans.lower()
        hit = next((n for n in _GEM_NAMES if re.search(rf"\b{re.escape(n)}\b", low)), None)
        if hit:
            problems.append(f"names a gemstone ({hit}); this answer has no stone list to support it")
    if "gems" in facts:
        asked = facts["gems"].get("asked") or []
        listed = " ".join(r["gem"].lower() for r in
                          facts["gems"]["recommended"] + facts["gems"]["avoid"] + asked)
        low = ans.lower()
        for name in _GEM_NAMES:
            if name in low and name not in listed:
                problems.append(f"names a gemstone ({name}) that is not in the supplied list")
                break
        if asked:
            for r in asked:
                first = r["gem"].split("(")[0].split("/")[0].strip().lower()
                alt = re.search(r"\(([^)]+)\)", r["gem"])           # 'Neelam' in 'Blue Sapphire (Neelam)'
                names = [first] + ([alt.group(1).strip().lower()] if alt else [])
                sents = [s for s in re.split(r"(?<=[.!?])\s", low) if any(n in s for n in names)]
                if not sents:
                    problems.append(f"never says whether {r['gem']} suits the reader")
                    break
                neg = re.search(r"\b(avoid|not|don't|do not|skip|shouldn't|unsafe|unsuitable|instead|isn't|"
                                r"no)\b", sents[0])
                pos = re.search(r"\b(suits?|suitable|wear|good|supportive|favou?rable|recommended|benefic)", sents[0])
                if r["verdict"] == "wear" and neg and not pos:
                    problems.append(f"says {r['gem']} is not for the reader, but the audit says it suits them")
                    break
                if r["verdict"] != "wear" and not neg:
                    problems.append(f"does not say {r['gem']} should be avoided; the audit says it is not for "
                                    f"the reader")
                    break
        else:
            for r in facts["gems"]["recommended"] + facts["gems"]["avoid"]:
                first = r["gem"].split("(")[0].split("/")[0].strip().lower()
                if first not in low:
                    problems.append(f"leaves out {r['gem']}")
                    break
    return problems


_GEM_QUESTION = re.compile(
    r"\b(gem|gems|gemstone|gemstones|stone|stones|ratna|rudraksha|ruby|pearl|coral|emerald|sapphire|"
    r"diamond|hessonite|gomed|cat'?s eye|manik|moti|moonga|panna|neelam|pukhraj|heera|lehsunia)\b", re.I)


def is_gem_question(question: str) -> bool:
    """A question about wearing a stone is answered from the stone audit, whatever life area it names."""
    return bool(_GEM_QUESTION.search(question or ""))


def _llm_allowed() -> bool:
    try:
        from core.config import S
        return bool(S.llm_tab_enabled("user_question"))
    except Exception:  # noqa: BLE001
        return False


def _blend_stance(hint: str, model: str, facts: dict) -> str:
    """The model may nuance by one step; it may not flip the outlook the chart signals give."""
    if facts["domain_key"] == "gemstones_remedies" or hint == "not_astrological":
        return hint
    if {hint, model} == {"favourable", "difficult"} or model == "not_astrological":
        return hint
    if hint == "mixed" and facts.get("lenses"):
        return hint           # the model may soften a verdict, never sharpen a balanced one
    return model


def _ask_model(facts: dict, lang: str) -> Optional[QuestionReading]:
    if facts["domain_key"] == "out_of_domain" or not _llm_allowed():
        return None
    try:
        from core.llm_client import complete_model
    except Exception:  # noqa: BLE001
        return None
    lk = _lang_key(lang)
    system = _SYSTEM          # always judged in English; non-English wording comes from templates
    user = _prompt(facts)
    judged: Optional[QuestionJudgement] = None
    problems: list[str] = []
    for attempt in range(4):
        try:
            got = complete_model(
                QuestionJudgement, system,
                user if not problems else user + "\n\nYour previous answer was rejected: "
                + "; ".join(problems[:3]) + ". Rewrite it in everyday words using only the PLAIN FACTS.",
                temperature=(0.2, 0.5, 0.7, 0.3)[attempt])
        except Exception as exc:  # noqa: BLE001
            print(f"[question_reading] model call failed: {type(exc).__name__}: {exc}", flush=True)
            return None
        if got is None:
            return None
        problems = _check(f"{got.answer.strip()} {got.because.strip()}".strip(), facts)
        if not problems:
            judged = got
            break
    if judged is None:
        print(f"[question_reading] model answer rejected: {problems[:3]}", flush=True)
        return None

    if "gems" in facts:
        why = _gem_why(facts, lk)
    else:
        why = _pick_why(facts, lk, judged.use)
    stance = _blend_stance(_stance_hint(facts), judged.stance, facts)
    timing = _timing_line(facts, lk) if _wants_timing(facts, judged.needs_timing) else ""
    answer = f"{judged.answer.strip()} {judged.because.strip()}".strip()
    if lk != "en":
        import question_reading_i18n as I18N
        answer = I18N.answer(facts, stance, lk)
    return _attach(QuestionReading(stance=stance, answer=answer, why=why, timing=timing,
                                   steps=_steps(facts, lk)), facts)


def _pick_why(facts: dict, lk: str, use: list[str]) -> list[str]:
    """The reasons the model chose, always covering the birth promise AND something running now."""
    rows = _findings_full(facts, lk)
    by_id = {fid: (lens, text) for fid, lens, text in rows}
    has_vuln = any(l == "vulnerability" for _i, l, _t in rows)
    cap = 6 if has_vuln else 5
    chosen = [i for i in dict.fromkeys(x.strip().upper() for x in use) if i in by_id][:cap]
    if len(chosen) < 3:
        seen = {by_id[i][0] for i in chosen}
        for fid, lens, _t in rows:           # no usable pick: the lead sentence of every lens
            if lens not in seen:
                chosen.append(fid)
                seen.add(lens)
    # Always shown: the birth promise, something running now, and (health) the body vulnerability.
    first_live = next((l for _i, l, _t in rows if l not in ("promise", "vulnerability")), "")
    has_naadi = any(l == "naadi" for _i, l, _t in rows)
    # Chandra Naadi reads the present moment, so it is reviewed - and shown - for every question.
    wants = (["promise"] + ([first_live] if first_live else []) + (["naadi"] if has_naadi else [])
             + (["vulnerability"] if has_vuln else []))
    for want in wants:
        if want in {by_id[i][0] for i in chosen}:
            continue
        fid = next(i for i, l, _t in rows if l == want)
        if len(chosen) >= cap:               # make room by dropping a reason that is not a required lens
            drop = next((i for i in reversed(chosen) if by_id[i][0] not in wants), chosen[-1])
            chosen.remove(drop)
        chosen.append(fid)
    votes = {k: v.get("vote", 0) for k, v in (facts.get("lenses") or {}).items()}
    while len(chosen) > 6:                    # trim: a lens that voted neutral goes first
        pool = [i for i in chosen if by_id[i][0] not in wants] or chosen
        chosen.remove(next((i for i in reversed(pool) if votes.get(by_id[i][0], 0) == 0), pool[-1]))
    order = [fid for fid, _l, _t in rows]
    return [by_id[i][1] for i in sorted(set(chosen), key=order.index)]


def plain_reasons(facts: dict, lang: str = "en") -> list[str]:
    """Customer-facing reasons; the selected technical findings stay in the collapsible proof."""
    lk = _lang_key(lang)
    if lk != "en":
        import question_reading_i18n as I18N
        return I18N.plain_reasons(facts, lk)
    key = facts["domain_key"]
    if key == "out_of_domain":
        return []
    if key == "gemstones_remedies":
        asked = facts["gems"].get("asked") or []
        first = ("This stone matches supportive factors in your chart, but comfort during the trial still matters."
                 if asked and all(r["verdict"] == "wear" for r in asked) else
                 "These stones match supportive factors in your chart, but individual comfort still matters."
                 if not asked else
                 "A stone that suits one chart may not suit another, so the cautious option is preferred here.")
        return [first, "The three-day trial is a precaution, not a guarantee; stop if you feel uncomfortable."]
    lenses = facts.get("lenses") or {}
    vuln = lenses.get("vulnerability")
    if vuln:
        import question_health as QH
        body = QH.text_en(vuln).split(" Chandra Naadi marks", 1)[0].strip()
        if body.startswith("Chandra Naadi"):
            body = "Your chart highlights specific body areas where stress may show first."
        rows = [body]
        rows.append("The present phase suggests extra care, so steady routines and early attention matter."
                    if _care_now(facts) else
                    "The present phase looks steadier, but regular care is still important.")
        return rows
    p, _n = _verdict_key(facts)
    subject, _verb = _answer_area(facts)
    area = subject[0].lower() + subject[1:]
    first = {
        1: f"Your chart gives {area} a supportive base to work from.",
        0: f"Your chart shows both support and strain for {area}, so effort and timing matter together.",
        -1: f"Your chart puts more pressure on {area}, so consistency matters more than a quick result.",
    }[p]
    rows = [first]
    vim = lenses.get("vimshottari") or {}
    rel = vim.get("rel", "none")
    who = vim.get("who") or ""
    phase = f"current {who} phase" if who else "current phase"
    rows.append({
        "helper": f"The {phase} is directly connected with this question, giving practical efforts more support.",
        "hard": f"The {phase} is linked with delay or pressure, so progress may be slower even with a supportive base.",
        "none": f"The {phase} is fairly neutral for this question, so preparation and personal choices matter more.",
    }[rel])
    naadi = lenses.get("naadi") or {}
    if naadi.get("cautions"):
        key = facts["domain_key"]
        caution = {
            "marriage_relationship": "keep communication calm and avoid rushed commitments",
            "career_profession": "avoid impulsive resignations or workplace conflicts",
            "wealth_finances": "avoid rushed financial commitments",
            "property_assets": "double-check documents and avoid rushed commitments",
            "children_progeny": "keep plans flexible and avoid putting extra pressure on yourself",
            "education_learning": "avoid last-minute changes to your preparation",
            "foreign_relocation": "double-check documents and avoid rushed bookings",
            "litigation_disputes": "avoid heated exchanges and follow qualified legal advice",
            "speech_neurology": "communicate slowly and avoid unnecessary strain",
        }.get(key, "avoid rushed decisions")
        if key == "career_profession":
            q = facts["question"].lower()
            if re.search(r"first\s+job|unemployed", q):
                caution = "keep applications consistent and do not treat delays as a final verdict"
            elif re.search(r"business|startup|self\s*-?\s*employ", q):
                caution = "avoid rushed investments or resigning before the plan is financially ready"
            elif "retir" in q:
                caution = "avoid rushed financial or retirement decisions"
            elif re.search(r"what\s+career|which\s+career|career\s+(?:should|direction)|choose.*career", q):
                caution = "explore steadily and avoid choosing only under family or peer pressure"
        rows.append(f"The immediate picture is sensitive, so {caution}.")
    return rows


def _attach(reading: QuestionReading, facts: dict) -> QuestionReading:
    """Record how the lenses voted, so the page can show them and the verdict is auditable."""
    lenses = facts.get("lenses") or {}
    if lenses:
        import question_lenses as QL
        reading.lenses = [{"key": k, "vote": lenses[k]["vote"]} for k in QL.LENS_ORDER if k in lenses]
        reading.confidence = QL.confidence(lenses)
    return reading


_VERDICT_AREA_EN = {
    (1, 1): "{area} {verb} well supported right now.",
    (1, 0): "{area} {verb} supportive overall, though the near term may feel uneven.",
    (1, -1): "{area} {verb} supportive at the base, but current delays call for patience.",
    (0, 1): "{area} {verb} mixed, but steady effort has useful support right now.",
    (0, 0): "{area} {verb} mixed, so expect some stops and starts rather than a quick result.",
    (0, -1): "{area} {verb} mixed and under pressure, so avoid rushing important decisions.",
    (-1, 1): "{area} {verb} demanding, although steady effort has some useful support right now.",
    (-1, 0): "{area} {verb} demanding and may take persistence, with no clear shortcut right now.",
    (-1, -1): "{area} {verb} difficult right now, so go carefully rather than forcing a quick result.",
}


def _answer_area(facts: dict) -> tuple[str, str]:
    key = facts["domain_key"]
    q = facts["question"].lower()
    if key == "career_profession":
        if "promot" in q:
            return "Your promotion prospects", "look"
        if re.search(r"first\s+job|unemployed", q):
            return "Your first-job prospects", "look"
        if re.search(r"business|startup|self\s*-?\s*employ", q):
            return "Your business plans", "look"
        if "retir" in q:
            return "Your retirement transition", "looks"
        if re.search(r"what\s+career|which\s+career|career\s+(?:should|direction)|choose.*career", q):
            return "Your career direction", "looks"
        if re.search(r"secure|security|safe|layoff|fired|demotion", q):
            return "Your job security", "looks"
        if re.search(r"change|switch|new job|another job", q):
            return "Your job-change prospects", "look"
    if key == "marriage_relationship":
        return ("Your marriage prospects", "look") if re.search(r"marri|wedding|shaadi|vivah", q) else ("Your relationship", "looks")
    if key == "foreign_relocation":
        if re.search(r"settl|permanent|relocate|move abroad", q):
            return "Your plans to settle abroad", "look"
        return "Your travel abroad plans", "look"
    if key == "children_progeny":
        return "Your path to parenthood", "looks"
    if key == "education_learning" and re.search(r"exam|test|clear|pass", q):
        return "Your exam prospects", "look"
    if key == "property_assets":
        if re.search(r"sell|sale", q):
            return "Your property sale prospects", "look"
        if re.search(r"transfer|gift", q):
            return "Your property transfer plans", "look"
    if key == "litigation_disputes":
        if "custody" in q:
            return "Your custody matter", "looks"
        if "divorce" in q:
            return "Your divorce proceedings", "look"
        if "inheritance" in q:
            return "Your inheritance dispute", "looks"
        if "tenant" in q:
            return "Your tenant dispute", "looks"
        if re.search(r"settle|settlement|mediation", q):
            return "Your settlement prospects", "look"
        if "property" in q:
            return "Your property dispute", "looks"
        if re.search(r"court|case", q):
            return "Your court case", "looks"
    area = {
        "health_vitality": "Your health", "speech_neurology": "Your speech and communication",
        "career_profession": "Your career", "wealth_finances": "Your finances",
        "education_learning": "Your studies", "property_assets": "Your property plans",
        "litigation_disputes": "Your legal matter", "general_destiny": "Your life path",
    }.get(key, "Your outlook")
    return area, "look" if area in ("Your finances", "Your studies", "Your property plans", "Your speech and communication") else "looks"


def verdict_opener(facts: dict) -> str:
    """The first sentence of the answer; it names the area asked about, never just 'this'."""
    p, n = _verdict_key(facts)
    if facts["domain_key"] == "health_vitality":
        if _care_now(facts) or n < 0:
            return ("Your health has a supportive base, but this is a time for extra care and steady routines."
                    if p > 0 else
                    "Your health needs extra care right now, so keep routines steady and do not ignore persistent discomfort.")
        return ("Your health needs consistent care, although the present phase looks steadier." if p < 0 else
                "Your health looks reasonably supported right now, with regular care still important.")
    area, verb = _answer_area(facts)
    return _VERDICT_AREA_EN[(p, n)].format(area=area, verb=verb)


def headline(answer: str, limit: int = 140) -> str:
    """The first whole sentence of the answer: it is shown as the page title, so never cut mid-phrase."""
    text = re.sub(r"\s+", " ", str(answer or "")).strip()
    first = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0]
    if len(first) <= limit:
        return first
    lead = first.split(";")[0].rstrip(",:- ")
    if ";" in first and len(lead) <= limit:
        return lead + "."
    cut = first[:limit].rsplit(" ", 1)[0].rstrip(",;:- ")
    return cut + "..."


def _verdict_key(facts: dict) -> tuple[int, int]:
    import question_lenses as QL
    return QL.promise_and_now(facts.get("lenses") or {})


# ----------------------------------------------------------------------- the fallback
def _fallback(facts: dict, lang: str = "en") -> QuestionReading:
    lk = _lang_key(lang)
    if lk != "en":
        import question_reading_i18n as I18N
        key = facts["domain_key"]
        if key == "out_of_domain":
            return QuestionReading(stance="not_astrological", answer=I18N.answer(facts, "mixed", lk),
                                   why=[], timing="", steps=[])
        if key == "gemstones_remedies":
            rec = facts["gems"]["recommended"]
            return _attach(QuestionReading(stance=_stance_hint(facts),
                                           answer=I18N.answer(facts, "mixed", lk), why=_gem_why(facts, lk),
                                           timing="", steps=_steps(facts, lk)), facts)
        stance = _stance_hint(facts)
        return _attach(QuestionReading(
            stance=stance, answer=I18N.answer(facts, stance, lk),
            why=_pick_why(facts, lk, []),
            timing=_timing_line(facts, lk) if _wants_timing(facts) else "", steps=_steps(facts, lk)), facts)
    key = facts["domain_key"]
    if key == "out_of_domain":
        return QuestionReading(
            stance="not_astrological",
            answer=("This looks like a question outside what a birth chart can answer. Ask about your "
                    "career, relationships, money, health, family, travel or timing and your chart "
                    "will answer it."),
            why=[], timing="", steps=[])
    if key == "gemstones_remedies" and facts["gems"].get("asked"):
        return _attach(QuestionReading(stance=_stance_hint(facts), answer=_asked_answer(facts),
                                       why=_gem_why(facts), timing="", steps=_steps(facts)), facts)
    if key == "gemstones_remedies":
        rec, avoid = facts["gems"]["recommended"], facts["gems"]["avoid"]
        if rec:
            names = _and_join([r["gem"] for r in rec])
            answer = (f"For your {facts['lagna']} rising sign, {names} "
                      f"{'is' if len(rec) == 1 else 'are'} the better-matched option{'s' if len(rec) > 1 else ''}.")
        else:
            answer = ("No gemstone is clearly safe for your chart right now, so the better route is "
                      "mantra and charity rather than wearing a stone.")
        if avoid:
            answer += " Avoid " + _and_join([r["gem"] for r in avoid[:3]]) + "."
        return QuestionReading(stance="favourable" if rec else "mixed", answer=answer,
                               why=_gem_why(facts), timing="", steps=_steps(facts))

    stance = _stance_hint(facts)
    opener = verdict_opener(facts)
    vuln = (facts.get("lenses") or {}).get("vulnerability")
    if vuln:                  # health: say where to take care instead of repeating the ruling planet
        import question_health as QH
        answer = f"{opener} {QH.answer_line(vuln)}".strip()
    else:
        answer = opener
    why = _pick_why(facts, "en", [])
    timing = _timing_line(facts) if _wants_timing(facts) else ""
    return _attach(QuestionReading(stance=stance, answer=answer, why=why, timing=timing,
                                   steps=_steps(facts)), facts)


def build_reading(conf: Any, pc: dict, cfg: dict, *, lang: str = "en") -> tuple[QuestionReading, dict, bool]:
    """Returns (reading, fact sheet, written_by_model)."""
    facts = build_fact_sheet(conf, pc, cfg)
    reading = _ask_model(facts, lang)
    if reading is not None:
        return reading, facts, True
    return _fallback(facts, lang), facts, False



# ------------------------------------------------------------------------- rendering
_LABELS = {
    "en": {
        "kicker": "Your question", "why": "What your chart shows", "when": "When",
        "do": "What to do", "facts": "Chart facts behind this answer",
        "favourable": "Looks favourable", "mixed": "Mixed", "difficult": "Needs care",
        "not_astrological": "Outside astrology",
        "lenses": "How the lenses line up",
        "lens_promise": "Birth promise", "lens_vimshottari": "Running period", "lens_jaimini": "Chara period",
        "lens_yogini": "Yogini", "lens_transit": "Transit", "lens_naadi": "Chandra Naadi",
        "lens_vulnerability": "Body vulnerability",
        "lens_kp": "Chart's promise", "lens_ruling": "Ruling planets", "lens_period": "Running period",
        "lens_moment": "Moment chart", "lens_jamakkol": "Tamil method", "lens_moon": "Moon now",
        "lock": "A dated window has been worked out for your question, with steps that suit your chart",
        "lockchip": "See when, and what to do",
        "cta": "Unlock full answer", "sub": "The window we calculated for this question, and the steps that suit it.",
        "lens_count": "{n} more perspectives were checked on your chart. What each one found is in the full reading.",
        "more_why": "{n} more reasons from your chart are in the full reading.",
        "deeper": "Every perspective in detail",
    },
    "hi_en": {
        "kicker": "Aapka prashna", "why": "Aapki kundli kya dikhati hai", "when": "Kab",
        "do": "Kya karein", "facts": "Is jawab ke peeche kundli ke tathya",
        "favourable": "Anukool", "mixed": "Milajula", "difficult": "Savdhani zaroori",
        "not_astrological": "Jyotish se bahar",
        "lenses": "Lens kaise milte hain",
        "lens_promise": "Kundli ka vachan", "lens_vimshottari": "Chal rahi dasha", "lens_jaimini": "Chara dasha",
        "lens_yogini": "Yogini", "lens_transit": "Gochar", "lens_naadi": "Chandra Naadi",
        "lens_vulnerability": "Sharir ki sanvedansheelta",
        "lens_kp": "Kundli ka vachan", "lens_ruling": "Shasak grah", "lens_period": "Chal rahi dasha",
        "lens_moment": "Prashna kundli", "lens_jamakkol": "Tamil vidhi", "lens_moon": "Abhi Chandra",
        "lock": "Aapke prashna ke liye ek tarikh-wali avadhi nikali gayi hai, aapki kundli ke anuroop kadam ke saath",
        "lockchip": "Kab aur kya karein, dekhein",
        "cta": "Poora jawab unlock karein", "sub": "Is prashna ke liye nikali gayi avadhi aur uske anuroop kadam.",
        "lens_count": "Aapki kundli par {n} aur drishtikon jaanche gaye. Har ek ne kya paya, yeh poori reading mein hai.",
        "more_why": "Aapki kundli ke {n} aur karan poori reading mein hain.",
        "deeper": "Har drishtikon vistaar mein",
    },
    "te_en": {
        "kicker": "Mee prashna", "why": "Mee kundali emi chupisthundi", "when": "Eppudu",
        "do": "Em cheyali", "facts": "Ee samadhanam venuka kundali vivaralu",
        "favourable": "Anukoolam", "mixed": "Mishramam", "difficult": "Jagrattha avasaram",
        "not_astrological": "Jyotishyam bayata",
        "lenses": "Lens lu ela kalustayi",
        "lens_promise": "Jataka vagdanam", "lens_vimshottari": "Nadustunna dasha", "lens_jaimini": "Chara dasha",
        "lens_yogini": "Yogini", "lens_transit": "Gochar", "lens_naadi": "Chandra Naadi",
        "lens_vulnerability": "Sharira sunnitatvam",
        "lens_kp": "Kundali vagdanam", "lens_ruling": "Shasaka grahalu", "lens_period": "Nadustunna dasha",
        "lens_moment": "Ee kshanam chart", "lens_jamakkol": "Tamil paddhati", "lens_moon": "Ippudu Chandrudu",
        "lock": "Mee prashnaku oka tedee-tho unna samayam lekkinchabadindi, mee kundaliki saripoye steps tho",
        "lockchip": "Eppudu, em cheyali chudandi",
        "cta": "Poorthi samadhanam unlock cheyandi", "sub": "Ee prashnaku lekkinchina samayam mariyu daaniki saripoye steps.",
        "lens_count": "Mee kundali meeda inka {n} drukkonalu parishilincham. Prathidi emi chupindo poorthi reading lo undi.",
        "more_why": "Mee kundali nundi inka {n} karanalu poorthi reading lo unnayi.",
        "deeper": "Prathi drukkonam vivaramga",
    },
}
_STANCE_COLOR = {"favourable": "#1c6b45", "mixed": "#8a6a1f", "difficult": "#a3341f",
                 "not_astrological": "#6a7080"}


def _esc(text: str) -> str:
    return html.escape(str(text or "").strip())


def _facts_list(facts: dict) -> list[str]:
    rows = [f"Rising sign {facts['lagna']}, Moon in {facts['moon_sign']}."]
    h = facts["house"]
    if facts["domain_key"] not in ("gemstones_remedies", "out_of_domain"):
        lord = h["lord"]
        rows.append(f"{_ord(h['number'])} house ({h['sign']}), ruled by {lord['planet']} in house "
                    f"{lord['house']} ({lord['sign']}).")
        for k in facts["karakas"]:
            rows.append(f"{k['planet']} (natural indicator): house {k['house']}, {k['sign']}.")
        if h["sav"]:
            rows.append(f"Sign score of the {_ord(h['number'])} house: {h['sav']} (average 28).")
        p = facts["periods"]
        if p["main"]:
            rows.append(f"{p['main']} main period until {p['main_until']}; {p['sub']} sub-period "
                        f"{p['sub_from']} to {p['sub_until']}.")
        if facts["transits"]:
            rows.append(facts["transits"][0].upper() + facts["transits"][1:] + ".")
        lenses = facts.get("lenses") or {}
        if "jaimini" in lenses:
            j = lenses["jaimini"]
            rows.append(f"Chara period: {j['maha']} main, {j['antar']} sub.")
        if "yogini" in lenses:
            y = lenses["yogini"]
            rows.append(f"Yogini period: {y['name']} ({y['lord']}), {y['tone']}.")
        if "naadi" in lenses:
            n = lenses["naadi"]
            where = f" in {n['moon_sign']}" if n["moon_sign"] else ""
            rows.append(f"Chandra Naadi: the Moon{where} is touching natal {', '.join(n['touched'])}."
                        if n["touched"] else f"Chandra Naadi: the Moon{where} is touching no natal planet.")
            if n.get("cautions"):
                import question_naadi as QN
                rows.append("Chandra Naadi caution: " + "; ".join(QN._CAUTION_EN[c] for c in n["cautions"]) + ".")
        if "vulnerability" in lenses:
            import question_health as QH
            rows.append("Body sensitivity: " + QH.text_en(lenses["vulnerability"]))
    return rows


def render_html(reading: QuestionReading, facts: dict, *, paid: bool, lang: str = "en",
                price: int = 298, fact_rows: Optional[list[str]] = None,
                meta_line: Optional[str] = None, extra_after_answer: str = "") -> str:
    """One card for any question. A horary supplies its own ``fact_rows`` and ``meta_line``."""
    L = _LABELS[_lang_key(lang)]
    color = _STANCE_COLOR[reading.stance]
    out_of_scope = reading.stance == "not_astrological"
    if meta_line is None:
        meta_line = f"{html.escape(facts['lagna'])} rising &middot; Moon in {html.escape(facts['moon_sign'])}"

    parts = [
        '<div class="uq-reading" style="margin:10px 0 24px;">',
        f'<article class="card" style="border-left:4px solid {color};background:#fff;border-radius:12px;'
        f'padding:18px 22px;margin-bottom:14px;box-shadow:0 2px 8px rgba(0,0,0,.03);">'
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px;margin-bottom:6px;">'
        f'<span style="font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;font-weight:700;color:#6a7080;">'
        f'{L["kicker"]}</span>'
        f'<span class="pill" style="font-size:.68rem;font-weight:700;padding:3px 10px;border-radius:99px;'
        f'background:#fbf6e4;color:{color};">{L[reading.stance]}</span></div>'
        f'<h2 style="font-family:Georgia,serif;font-size:1.2rem;margin:4px 0 10px;color:#1f2430;font-weight:600;'
        f'line-height:1.35;">&ldquo;{_esc(facts["question"])}&rdquo;</h2>'
        f'<p style="font-size:1rem;line-height:1.6;color:#2c3140;margin:0 0 6px;">{_esc(reading.answer)}</p>'
        f'<p style="font-size:.78rem;color:#6a7080;margin:8px 0 0;">{meta_line}</p>'
        '</article>',
    ]
    if extra_after_answer and not out_of_scope:
        parts.append(extra_after_answer)       # e.g. the relationship reading

    free_view = not paid and not out_of_scope
    if reading.lenses and free_view:
        n_lens = len([v for v in reading.lenses if int(v.get("vote", 0)) in (1, 0, -1)])
        if n_lens:
            parts.append(
                '<div class="uq-lenses" style="margin:0 0 14px;padding:10px 14px;background:#fff;'
                'border:1px solid #e8e4dc;border-radius:12px;font-size:.84rem;line-height:1.5;color:#4a5160;">'
                f'&#128269; {L["lens_count"].format(n=n_lens)}</div>')
    elif reading.lenses:
        chip = {1: ("&#10003;", "#1c6b45", "#e9f5ee"), 0: ("&bull;", "#8a6a1f", "#fbf6e4"),
                -1: ("&#10007;", "#a3341f", "#fbeae6")}
        chips = "".join(
            f'<span style="display:inline-flex;align-items:center;gap:5px;font-size:.74rem;font-weight:600;'
            f'padding:4px 10px;border-radius:99px;background:{chip[int(v["vote"])][2]};'
            f'color:{chip[int(v["vote"])][1]};">{chip[int(v["vote"])][0]} {L.get("lens_" + v["key"], v["key"])}</span>'
            for v in reading.lenses if int(v.get("vote", 0)) in chip)
        parts.append(
            '<div class="uq-lenses" style="margin:0 0 14px;padding:10px 14px;background:#fff;'
            'border:1px solid #e8e4dc;border-radius:12px;">'
            f'<div style="font-size:.68rem;letter-spacing:.12em;text-transform:uppercase;font-weight:800;'
            f'color:#6a7080;margin-bottom:6px;">{L["lenses"]}</div>'
            f'<div style="display:flex;flex-wrap:wrap;gap:6px;">{chips}</div></div>')

    if reading.why:
        shown = reading.why[:2] if free_view else reading.why
        hidden = len(reading.why) - len(shown)
        items = "".join(f'<li style="margin-bottom:6px;">{_esc(w)}</li>' for w in shown)
        if hidden > 0:
            items += (f'<li style="margin-bottom:6px;list-style:none;margin-left:-18px;color:#8a5a1c;'
                      f'font-size:.84rem;">&#128274; {L["more_why"].format(n=hidden)}</li>')
        parts.append(
            '<article class="card" style="background:#fff;border:1px solid #e8e4dc;border-radius:12px;'
            'padding:16px 20px;margin-bottom:14px;">'
            f'<div style="font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;font-weight:800;'
            f'color:#7a4b18;margin-bottom:8px;">{L["why"]}</div>'
            f'<ul style="margin:0;padding-left:18px;font-size:.92rem;line-height:1.55;color:#2c3140;">{items}</ul>'
            '</article>')

    has_more = bool(reading.timing.strip() or reading.steps)
    if has_more and (paid or out_of_scope):
        block = ""
        if reading.timing.strip():
            block += (f'<p style="margin:0 0 10px;font-size:.92rem;line-height:1.55;color:#2c3140;">'
                      f'<b>{L["when"]}:</b> {_esc(reading.timing)}</p>')
        if reading.steps:
            li = "".join(f'<li style="margin-bottom:6px;">{_esc(s)}</li>' for s in reading.steps)
            block += (f'<div style="font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;font-weight:800;'
                      f'color:#1c6b45;margin:4px 0 6px;">{L["do"]}</div>'
                      f'<ul style="margin:0;padding-left:18px;font-size:.92rem;line-height:1.55;color:#2c3140;">{li}</ul>')
        parts.append('<article class="card" style="background:#f9fbf9;border:1px solid #d4e8dc;'
                     'border-left:4px solid #1c6b45;border-radius:12px;padding:16px 20px;margin-bottom:14px;">'
                     + block + '</article>')
    elif has_more:
        parts.append(
            '<div class="lock-wrap" data-unlock="1" role="button" tabindex="0" '
            'style="margin:16px 0;border-radius:12px;cursor:pointer;">'
            f'<div class="lock-blur" style="padding:16px 20px;font-size:.88rem;line-height:1.55;">'
            f'<b>{L["when"]}:</b> {L["lock"]}.</div>'
            f'<div class="lock-over" data-unlock="1"><span class="lock-chip" data-unlock="1" '
            f'style="font-size:.72rem;padding:7px 18px;cursor:pointer;">&#128274; {L["lockchip"]}</span></div></div>'
            '<div class="buy" style="margin:16px 0;background:linear-gradient(135deg,#1f2430 0%,#141720 100%);'
            'border:1px solid #c9a227;border-radius:14px;padding:20px;text-align:center;color:#fff;">'
            f'<p style="font-size:.88rem;color:#b8bdcc;margin:0 0 14px;line-height:1.5;">{L["sub"]}</p>'
            '<a class="cta" href="#unlock" data-unlock="1" style="cursor:pointer;display:inline-flex;'
            'align-items:center;justify-content:center;background:linear-gradient(135deg,#e8b75b 0%,#c9a227 100%);'
            'color:#16181d;font-weight:700;font-size:.95rem;padding:12px 26px;border-radius:99px;'
            f'text-decoration:none;width:100%;max-width:320px;">&#128274; {L["cta"]} &mdash; &#8377;{int(price)}</a>'
            '</div>')

    if paid and not out_of_scope:
        try:
            have = {str(w).strip() for w in reading.why}
            extra = [t for _fid, _l, t in _findings_full(facts, lang) if t.strip() not in have][:6]
        except Exception:
            extra = []
        if extra:
            li = "".join(f'<li style="margin-bottom:6px;">{_esc(t)}</li>' for t in extra)
            parts.append(
                '<article class="card" style="background:#fff;border:1px solid #e8e4dc;border-radius:12px;'
                'padding:16px 20px;margin-bottom:14px;">'
                f'<div style="font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;font-weight:800;'
                f'color:#7a4b18;margin-bottom:8px;">{L["deeper"]}</div>'
                f'<ul style="margin:0;padding-left:18px;font-size:.92rem;line-height:1.55;color:#2c3140;">{li}</ul>'
                '</article>')

    if fact_rows is None:
        fact_rows = _facts_list(facts)
    if paid and not out_of_scope and len(fact_rows) >= 3:
        rows = "".join(f'<li style="margin-bottom:4px;">{_esc(r)}</li>' for r in fact_rows)
        parts.append(
            '<details class="astro-proof-details" style="background:#fcfbf8;border:1px solid #e8e4dc;'
            'border-radius:10px;padding:12px 16px;margin:14px 0;">'
            f'<summary style="cursor:pointer;font-size:.82rem;font-weight:700;color:#7a4b18;">{L["facts"]}</summary>'
            f'<ul style="margin:10px 0 0;padding-left:18px;font-size:.84rem;line-height:1.55;color:#444;">{rows}</ul>'
            '</details>')
    parts.append("</div>")
    return "\n".join(parts)





