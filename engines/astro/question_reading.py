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
    if conf.domain_key not in ("gemstones_remedies", "general_destiny", "out_of_domain"):
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
    if conf.domain_key not in ("gemstones_remedies", "general_destiny", "out_of_domain"):
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
        facts["gems"] = {"recommended": rec, "avoid": avoid}
    return facts


def _short_avoid_reason(inf: dict) -> str:
    text = " ".join(inf.get("reasons") or [])
    if "8th house" in text and "placed in the 8th" in text:
        return "it sits in your 8th house, which stirs up sudden trouble"
    if "Dusthana" in text:
        return "it rules a difficult house (6th, 8th or 12th) and could magnify those problems"
    if "Kendradhipati" in text or "Maraka" in text:
        return "it rules a house of loss or obstruction for your rising sign"
    return "it is not a safe stone for your chart"


def _stance_hint(facts: dict) -> str:
    n_for, n_against = len(facts["signals_for"]), len(facts["signals_against"])
    if facts["domain_key"] == "gemstones_remedies":
        return "favourable" if facts["gems"]["recommended"] else "mixed"
    if facts["domain_key"] == "out_of_domain":
        return "not_astrological"
    if facts.get("lenses"):
        import question_lenses as QL
        return QL.stance(facts["lenses"])
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
    w = facts.get("next_window") or ""
    return f"The period that supports this most is {w}." if w else ""


_WHEN_WORDS = re.compile(r"\b(when|how long|by when|which year|what year|how soon|kab|eppudu|date|timing|time)\b", re.I)


def _wants_timing(facts: dict, flag: Optional[bool] = None) -> bool:
    if facts["domain_key"] in ("gemstones_remedies", "out_of_domain"):
        return False
    # The model's flag only breaks a tie: a window is relevant for "will it happen" areas and for any
    # question that asks "when"; it is noise on "how is my health".
    return bool(_WHEN_WORDS.search(facts["question"])) or facts["domain_key"] in _MOVE_DOMAINS


def _steps(facts: dict, lang: str = "en") -> list[str]:
    if _lang_key(lang) != "en":
        import question_reading_i18n as I18N
        return I18N.steps(facts, _lang_key(lang))
    key = facts["domain_key"]
    if key == "gemstones_remedies":
        rec = facts["gems"]["recommended"]
        steps = [f"Wear {r['gem']} in {r['metal'].lower()} on the {r['finger'].lower()}, on a {r['day']} "
                 f"morning in the bright half of the month." for r in rec[:2]]
        if facts["gems"]["avoid"]:
            steps.append("Skip the stones listed as avoid; use that planet's mantra and a small "
                         "donation instead.")
        if not steps:
            lord = facts["lagna_lord"]
            steps.append(f"Chant {lord}'s mantra on {_WEEKDAY.get(lord, 'its day')}s and give a small donation.")
        return steps[:3]
    if key == "out_of_domain":
        return []
    steps = []
    # Work on the planet that is actually under strain; fall back to the first natural indicator.
    cands = [facts["house"]["lord"], *facts["karakas"]]
    weak = next((c for c in cands if c["hard_house"] or c["dignity"] in _BAD_DIGNITY or c["combust"]), None)
    target = weak or (facts["karakas"][0] if facts["karakas"] else None)
    if target:
        k = target["planet"]
        steps.append(f"Strengthen {k}: chant its mantra and offer a small donation on {_WEEKDAY.get(k, 'its day')}s.")
    window = facts.get("next_window")
    if window and key in _MOVE_DOMAINS:
        steps.append(f"Aim to make the key move during the {window} and prepare before it.")
    return steps[:3]


def _gem_why(facts: dict, lang: str = "en") -> list[str]:
    if _lang_key(lang) != "en":
        import question_reading_i18n as I18N
        return I18N.gem_why(facts, _lang_key(lang))
    why = []
    for r in facts["gems"]["recommended"]:
        hs = _and_join([_ord(int(h)) for h in r["houses"]])
        why.append(f"{r['planet']} rules your {hs} house{'s' if len(r['houses']) > 1 else ''}, "
                   f"which makes {r['gem']} a supportive stone for you.")
    for r in facts["gems"]["avoid"][:2]:
        why.append(f"{r['gem']} is best avoided because {r['reason']}.")
    return why[:4]


# ------------------------------------------------------------------------- the model
class QuestionJudgement(BaseModel):
    """What the model decides. It never writes a fact: reasons are picked by id."""
    model_config = ConfigDict(extra="forbid")

    stance: Stance
    answer: str = Field(description="ONE sentence, under 18 words, that directly answers the question asked, "
                                    "speaking to the reader as 'you'.")
    because: str = Field(default="", description="ONE sentence, under 30 words, using 'your': whether the birth "
                                                 "promise and what is running now agree, and the key fact.")
    use: list[str] = Field(description="Ids (F1, F2...) of the 3-5 findings that matter for THIS question.")
    needs_timing: bool = Field(description="True only if the question asks when / how long / which year.")


_SYSTEM = (
    "You are an experienced Vedic astrologer answering ONE question for one person. First work out "
    "what the question is really asking. Judge it by how the lenses line up: the birth promise "
    "(what the chart itself allows) against what is running now (the main and sub period, the Chara "
    "period, the Yogini period, transits, Chandra Naadi). Fill `answer` with one short sentence that "
    "answers the question in plain words, e.g. 'You can change jobs, but it will take effort'. Fill "
    "`because` with one sentence that says, using 'your', whether the birth promise and what is "
    "running now agree, naming the one or two facts that decide it. Use ONLY the numbered findings "
    "supplied; never add a planet position, house, date or gemstone that is not written there. In "
    "`use` list the ids of the 3-5 findings that genuinely matter for THIS question, covering both "
    "the birth promise and what is running now; leave out the rest. No headings, no jargon, no "
    "padding, do not repeat the question, never mention Lal Kitab. stance is favourable, mixed or "
    "difficult; stay close to the suggested stance unless a finding clearly says otherwise. Set "
    "needs_timing true only when the question asks about time. Never put a date, year or period "
    "length in the text: timing is shown separately."
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
        lines.append("Your answer MUST name every SUITS stone and every AVOID stone, in that order.")
    else:
        lens_labels = {"promise": "birth promise", "vimshottari": "running period", "jaimini": "Chara period",
                       "yogini": "Yogini", "transit": "transit", "naadi": "Chandra Naadi"}
        votes = facts.get("lenses") or {}
        if votes:
            word = {1: "supports", 0: "neutral", -1: "strains"}
            lines.insert(4, "How the lenses line up: " + "; ".join(
                f"{lens_labels[k]} {word[votes[k]['vote']]}" for k in lens_labels if k in votes) + ".")
        if votes:
            p, n = _verdict_key(facts)
            lines.insert(5, "Verdict frame (answer the question FIRST, then state both in one short sentence using your/you): your birth promise is "
                         f"{ {1: 'strong', 0: 'mixed', -1: 'weak'}[p] }; what is running for you now is "
                         f"{ {1: 'helping', 0: 'mixed', -1: 'holding it back'}[n] }.")
        for fid, lens, text in _findings_full(facts):
            lines.append(f"{fid} [{lens_labels.get(lens, lens)}]: {text}")
    return "\n".join(lines)


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
    if len(ans.split()) > 90:
        problems.append("answer is longer than 60 words")
    if re.search(r"lal\s*kitab|python|code|```", ans, re.I):
        problems.append("answer contains something that is not part of a chart answer")
    if re.search(r"\b20\d\d\b", ans):
        problems.append("puts a year in the answer; timing is shown separately")
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
        listed = " ".join(r["gem"].lower() for r in facts["gems"]["recommended"] + facts["gems"]["avoid"])
        low = ans.lower()
        for name in _GEM_NAMES:
            if name in low and name not in listed:
                problems.append(f"names a gemstone ({name}) that is not in the supplied list")
                break
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
    for attempt in range(3):
        try:
            got = complete_model(
                QuestionJudgement, system,
                user if not problems else user + "\n\nYour previous answer was rejected: "
                + "; ".join(problems[:3]) + ". Rewrite it using only the findings.",
                temperature=0.2)
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
    chosen = [i for i in dict.fromkeys(x.strip().upper() for x in use) if i in by_id][:5]
    if len(chosen) < 3:
        seen = {by_id[i][0] for i in chosen}
        for fid, lens, _t in rows:           # no usable pick: the lead sentence of every lens
            if lens not in seen:
                chosen.append(fid)
                seen.add(lens)
    lenses_in = {by_id[i][0] for i in chosen}
    for want in ("promise", next((l for _i, l, _t in rows if l != "promise"), "")):
        if want and want not in lenses_in:
            fid = next(i for i, l, _t in rows if l == want)
            chosen = (chosen[:4] + [fid]) if len(chosen) >= 5 else chosen + [fid]
            lenses_in.add(want)
    order = [fid for fid, _l, _t in rows]
    return [by_id[i][1] for i in sorted(set(chosen), key=order.index)]


def _attach(reading: QuestionReading, facts: dict) -> QuestionReading:
    """Record how the lenses voted, so the page can show them and the verdict is auditable."""
    lenses = facts.get("lenses") or {}
    if lenses:
        import question_lenses as QL
        reading.lenses = [{"key": k, "vote": lenses[k]["vote"]} for k in QL.LENS_ORDER if k in lenses]
        reading.confidence = QL.confidence(lenses)
    return reading


_VERDICT_EN = {
    (1, 1): "Your chart promises this and what is running now backs it.",
    (1, 0): "Your chart promises this, and what is running now is mixed, so steady effort will carry it.",
    (1, -1): "Your chart promises this, but what is running now is holding it back, so be patient.",
    (0, 1): "Your chart gives a mixed promise here, but what is running now helps.",
    (0, 0): "This is possible for you, but expect some effort and delay.",
    (0, -1): "Your chart gives a mixed promise here, and what is running now adds friction.",
    (-1, 1): "Your chart's promise here is weak, though what is running now helps, so effort pays now.",
    (-1, 0): "Your chart's promise here is weak and what is running now is mixed, so it will take effort.",
    (-1, -1): "This is not easy for you right now: the chart's promise is weak and what is running now "
              "adds friction.",
}


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
            return QuestionReading(stance="favourable" if rec else "mixed",
                                   answer=I18N.answer(facts, "mixed", lk), why=_gem_why(facts, lk),
                                   timing="", steps=_steps(facts, lk))
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
    if key == "gemstones_remedies":
        rec, avoid = facts["gems"]["recommended"], facts["gems"]["avoid"]
        if rec:
            names = " and ".join(r["gem"] for r in rec)
            answer = (f"For your {facts['lagna']} rising sign, {names} "
                      f"{'suits' if len(rec) == 1 else 'suit'} you best.")
        else:
            answer = ("No gemstone is clearly safe for your chart right now, so the better route is "
                      "mantra and charity rather than wearing a stone.")
        if avoid:
            answer += " Avoid " + ", ".join(r["gem"] for r in avoid[:3]) + "."
        return QuestionReading(stance="favourable" if rec else "mixed", answer=answer,
                               why=_gem_why(facts), timing="", steps=_steps(facts))

    stance = _stance_hint(facts)
    lord = facts["house"]["lord"]
    dw = _dignity_words(lord["dignity"])
    opener = _VERDICT_EN[_verdict_key(facts)]
    answer = (f"{opener} {lord['planet']}, the planet that rules this area, sits in house {lord['house']} "
              f"in {lord['sign']}" + (f" and is {dw}" if dw else "") + ".")
    if lord["hard_house"]:
        answer += " That house tends to slow things down."
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
        "lock": "Timing and next steps are in the full reading",
        "lockchip": "Unlock timing and steps",
        "cta": "Unlock full answer", "sub": "Timing window and practical steps for this question.",
    },
    "hi_en": {
        "kicker": "Aapka prashna", "why": "Aapki kundli kya dikhati hai", "when": "Kab",
        "do": "Kya karein", "facts": "Is jawab ke peeche kundli ke tathya",
        "favourable": "Anukool", "mixed": "Milajula", "difficult": "Savdhani zaroori",
        "not_astrological": "Jyotish se bahar",
        "lenses": "Lens kaise milte hain",
        "lens_promise": "Kundli ka vachan", "lens_vimshottari": "Chal rahi dasha", "lens_jaimini": "Chara dasha",
        "lens_yogini": "Yogini", "lens_transit": "Gochar", "lens_naadi": "Chandra Naadi",
        "lock": "Samay aur agle kadam poori reading mein hain",
        "lockchip": "Samay aur kadam unlock karein",
        "cta": "Poora jawab unlock karein", "sub": "Is prashna ka samay aur vyavaharik kadam.",
    },
    "te_en": {
        "kicker": "Mee prashna", "why": "Mee kundali emi chupisthundi", "when": "Eppudu",
        "do": "Em cheyali", "facts": "Ee samadhanam venuka kundali vivaralu",
        "favourable": "Anukoolam", "mixed": "Mishramam", "difficult": "Jagrattha avasaram",
        "not_astrological": "Jyotishyam bayata",
        "lenses": "Lens lu ela kalustayi",
        "lens_promise": "Jataka vagdanam", "lens_vimshottari": "Nadustunna dasha", "lens_jaimini": "Chara dasha",
        "lens_yogini": "Yogini", "lens_transit": "Gochar", "lens_naadi": "Chandra Naadi",
        "lock": "Samayam mariyu tarvata chese pani poorthi reading lo unnayi",
        "lockchip": "Samayam mariyu steps unlock cheyandi",
        "cta": "Poorthi samadhanam unlock cheyandi", "sub": "Ee prashnaku samayam mariyu practical steps.",
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
        if "naadi" in lenses and lenses["naadi"]["touched"]:
            n = lenses["naadi"]
            where = f" in {n['moon_sign']}" if n["moon_sign"] else ""
            rows.append(f"Chandra Naadi: the Moon{where} is touching natal {', '.join(n['touched'])}.")
    return rows


def render_html(reading: QuestionReading, facts: dict, *, paid: bool, lang: str = "en",
                price: int = 298) -> str:
    L = _LABELS[_lang_key(lang)]
    color = _STANCE_COLOR[reading.stance]
    out_of_scope = reading.stance == "not_astrological"
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

    if reading.lenses:
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
        items = "".join(f'<li style="margin-bottom:6px;">{_esc(w)}</li>' for w in reading.why)
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




