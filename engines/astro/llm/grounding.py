"""Ground chat / consultation prose in the tool output, not the model's memory.

The writer may only phrase what ``extract_ledger`` can see. Invented houses,
signs, gemstones, dates, or a 'this year' promise the windows do not support
are rejected so the caller can fall back to deterministic sentences built
from the same ledger.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable, Optional

PLANETS = (
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
    "Rahu", "Ketu",
)
SIGNS = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)
SIGN_LORDS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}
GEM_ALIASES: dict[str, tuple[str, ...]] = {
    "Emerald (Panna)": ("emerald", "panna", "emrald", "emerland"),
    "Ruby (Manik)": ("ruby", "manik"),
    "Pearl (Moti)": ("pearl", "moti"),
    "Red Coral (Moonga)": ("red coral", "moonga"),
    "Yellow Sapphire (Pukhraj)": ("yellow sapphire", "pukhraj"),
    "Diamond / White Zircon (Heera)": ("diamond", "heera", "white zircon", "opal"),
    "Blue Sapphire (Neelam)": ("blue sapphire", "neelam"),
    "Hessonite (Gomed)": ("hessonite", "gomed"),
    "Cat's Eye (Lehsunia)": ("cat's eye", "cats eye", "lehsunia", "lahsuniya"),
}
_NO_WEAR = {"AVOID", "STRICTLY_AVOID", "MANTRA_ONLY"}
_AVOID = {"AVOID", "STRICTLY_AVOID"}

_PLANET_RE = "|".join(p.lower() for p in PLANETS)
_SIGN_RE = "|".join(s.lower() for s in SIGNS)
_PLANET_IN_SIGN = re.compile(
    rf"\b({_PLANET_RE})\b(?:'s)?(?:\s+\w+){{0,10}}\s+in\s+(?:the\s+)?({_SIGN_RE})\b",
    re.I,
)
_PLANET_IN_HOUSE = re.compile(
    rf"\b({_PLANET_RE})\b(?:'s)?"
    rf".{{0,70}}?"
    rf"(?:occupies|sits(?:\s+in)?|seated(?:\s+in)?|placed(?:\s+in)?|is)?"
    rf"\s+in\s+"
    rf"(?:(?:the\s+)?(?:{_SIGN_RE})\s+(?:in\s+)?)?"
    rf"(?:the\s+)?(\d{{1,2}})(?:st|nd|rd|th)?\s+house\b",
    re.I,
)
_HOUSE_RULED_BY = re.compile(
    rf"(?:the\s+)?(\d{{1,2}})(?:st|nd|rd|th)?\s+house\s+"
    rf"(?:is\s+)?(?:governed by|ruled by|owned by)\s+({_PLANET_RE})\b",
    re.I,
)
_PLANET_SIGN_HOUSE = re.compile(
    rf"\b({_PLANET_RE})\b(?:\s+\w+){{0,8}}\s+in\s+({_SIGN_RE})\s+"
    rf"\((?:the\s+)?(\d{{1,2}})",
    re.I,
)
_HOUSE_IN_SIGN = re.compile(
    rf"(?:the\s+)?(\d{{1,2}})(?:st|nd|rd|th)?\s+house\s+"
    rf"(?:is\s+)?(?:in|of)\s+({_SIGN_RE})\b",
    re.I,
)
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_ISO_DATE = re.compile(r"\b(19|20)\d{2}-\d{2}-\d{2}\b")
_MONTH_YEAR = re.compile(
    r"\b(january|february|march|april|may|june|july|august|september|"
    r"october|november|december)\s+(?:(?:the\s+)?\d{1,2}(?:st|nd|rd|th)?,?\s+)?"
    r"((?:19|20)\d{2})\b",
    re.I,
)
_SCAFFOLD = re.compile(
    r"^#{1,4}\s+\w+"
    r"|^\*\*[A-Za-z].{0,40}\*\*\s*$"
    r"|^(?:CHART JUDGEMENT|LAL KITAB|CHANDRA NAADI|KEY POINTS|"
    r"TIMING(?: WINDOWS)?|RECOMMENDATIONS?|CONCLUSION)\s*:",
    re.I | re.M,
)
_INTERNAL_STATUS = re.compile(
    r"\b(HEALTHY_HARDWARE|STRICTLY_AVOID|MANTRA_ONLY|JOBLESS_FAILURE)\b",
)
_THIS_YEAR_YES = re.compile(
    r"\b(this year|later this year|before (?:the )?year(?:'s)? end)\b"
    r".{0,90}\b(possible|possibility|can |likely|chance|opportunity|"
    r"go ahead|buy|promotion|will get|indicate[sd]? a possibility)\b|"
    r"\b(possible|possibility|can |likely|chance|opportunity|will get|"
    r"indicate[sd]? a possibility)\b.{0,90}"
    r"\b(this year|later this year)\b",
    re.I,
)
_THIS_YEAR_NO = re.compile(
    r"\b(not|n't|no |wait|later|after|challeng|difficult|weak|mixed|"
    r"unlikely|do not|don't)\b.{0,50}\b(this year)\b|"
    r"\b(this year)\b.{0,50}\b(not |n't|challeng|difficult|weak|mixed|"
    r"unlikely|wait|later)\b",
    re.I,
)
_CLEAR_AVOID = re.compile(
    r"\b(avoid|do not wear|don't wear|not advis|not recommend|stay away|"
    r"skip wearing|against (?:you|your)|works against)\b",
    re.I,
)
_WEAR = re.compile(
    r"\b(wear|wearing|worn|put on|start wearing|recommend(?:ed)?|"
    r"suitable|good for you|try)\b",
    re.I,
)


def _canon_planet(name: str) -> str:
    low = str(name or "").strip().lower()
    for p in PLANETS:
        if p.lower() == low:
            return p
    return ""


def _canon_sign(name: str) -> str:
    low = str(name or "").strip().lower()
    for s in SIGNS:
        if s.lower() == low:
            return s
    return ""


def _as_int(value: Any) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return 0
    return n if 1 <= n <= 12 else 0


def _house_sign(lagna: str, house: int) -> str:
    if not lagna or house < 1:
        return ""
    try:
        idx = SIGNS.index(lagna)
    except ValueError:
        return ""
    return SIGNS[(idx + house - 1) % 12]


@dataclass
class Placement:
    house: int = 0
    sign: str = ""


@dataclass
class GemFact:
    label: str
    planet: str
    status: str
    aliases: tuple[str, ...]


@dataclass
class Ledger:
    natal: dict[str, Placement] = field(default_factory=dict)
    house_signs: dict[int, str] = field(default_factory=dict)
    house_lords: dict[int, str] = field(default_factory=dict)
    owned_houses: dict[str, set[int]] = field(default_factory=dict)
    transit_houses: dict[str, set[int]] = field(default_factory=dict)
    transit_signs: dict[str, set[str]] = field(default_factory=dict)
    gems: list[GemFact] = field(default_factory=list)
    gem_aliases: set[str] = field(default_factory=set)
    years: set[str] = field(default_factory=set)
    windows: list[str] = field(default_factory=list)
    this_year_supported: bool = False
    current_year: int = field(default_factory=lambda: date.today().year)
    verdict: str = ""
    breakthrough: str = ""
    lk_lines: list[str] = field(default_factory=list)
    cn_lines: list[str] = field(default_factory=list)
    judgement: str = ""
    lagna: str = ""
    lagna_lord: str = ""
    primary_house: int = 0
    primary_sign: str = ""
    primary_lord: str = ""

    def allowed_houses(self, planet: str) -> set[int]:
        out: set[int] = set()
        natal = self.natal.get(planet)
        if natal and natal.house:
            out.add(natal.house)
        out |= set(self.transit_houses.get(planet) or ())
        return out

    def allowed_signs(self, planet: str) -> set[str]:
        out: set[str] = set()
        natal = self.natal.get(planet)
        if natal and natal.sign:
            out.add(natal.sign)
        out |= set(self.transit_signs.get(planet) or ())
        return out


def _set_natal(ledger: Ledger, planet: str, house: int = 0, sign: str = "") -> None:
    planet = _canon_planet(planet)
    sign = _canon_sign(sign)
    house = _as_int(house)
    if not planet:
        return
    slot = ledger.natal.setdefault(planet, Placement())
    if house and not slot.house:
        slot.house = house
    if sign and not slot.sign:
        slot.sign = sign


def _add_years(ledger: Ledger, text: str) -> None:
    for y in _YEAR.findall(text or ""):
        ledger.years.add(y)
    for m in _ISO_DATE.finditer(text or ""):
        ledger.years.add(m.group(0)[:4])


_NATIVE = re.compile(
    r"\bthe (?:native|seeker|querent|client|chart holder)\b", re.I)


def _you(text: str) -> str:
    out = _NATIVE.sub("you", text or "")
    out = re.sub(r"\byou experiences\b", "you experience", out, flags=re.I)
    out = re.sub(r"\byou sits\b", "you sit", out, flags=re.I)
    return out


def _trim_line(value: Any, limit: int = 220) -> str:
    text = _you(" ".join(str(value or "").split()))
    if len(text) <= limit:
        return text
    cut = text[:limit]
    period = cut.rfind(". ")
    if period >= 80:
        return cut[:period + 1]
    space = cut.rfind(" ")
    return cut[:space] if space > 40 else cut


def _ingest_finding(bucket: list[str], item: Any) -> None:
    if len(bucket) >= 4:
        return
    if isinstance(item, str):
        line = _trim_line(item)
        if line:
            bucket.append(line)
        return
    if not isinstance(item, dict):
        return
    title = _trim_line(item.get("title") or "", 80)
    summary = _trim_line(item.get("summary") or item.get("result") or "", 180)
    line = f"{title}: {summary}".strip(": ")
    if line:
        bucket.append(line)


def _ingest_gem(ledger: Ledger, planet: str, info: dict[str, Any]) -> None:
    planet = _canon_planet(planet) or _canon_planet(info.get("planet") or "")
    label = str(info.get("gem") or "").strip()
    status = str(info.get("status") or "").strip().upper()
    aliases: list[str] = []
    for key, al in GEM_ALIASES.items():
        if label and (label.lower() in key.lower() or key.lower() in label.lower()):
            aliases.extend(al)
            if not label:
                label = key
    if label:
        aliases.append(label.lower())
        for token in re.findall(r"[a-z']{3,}", label.lower()):
            aliases.append(token)
    aliases = tuple(dict.fromkeys(a for a in aliases if a and a not in ("the", "and")))
    if label or status:
        ledger.gems.append(GemFact(label or planet, planet, status, aliases))
    ledger.gem_aliases.update(aliases)
    house = _as_int(info.get("house"))
    _set_natal(ledger, planet, house=house)
    owned = info.get("owned_houses") or []
    if planet and isinstance(owned, (list, tuple)):
        ledger.owned_houses.setdefault(planet, set()).update(
            h for h in (_as_int(x) for x in owned) if h)


def _fill_houses_from_lagna(ledger: Ledger) -> None:
    if not ledger.lagna:
        return
    for h in range(1, 13):
        sign = _house_sign(ledger.lagna, h)
        if sign:
            ledger.house_signs.setdefault(h, sign)
            lord = SIGN_LORDS.get(sign, "")
            if lord:
                ledger.house_lords.setdefault(h, lord)
                ledger.owned_houses.setdefault(lord, set()).add(h)
    for planet, slot in ledger.natal.items():
        if slot.house and not slot.sign:
            slot.sign = _house_sign(ledger.lagna, slot.house)


def _walk(obj: Any, ledger: Ledger, *, source: str = "") -> None:
    if obj is None:
        return
    if isinstance(obj, str):
        _add_years(ledger, obj)
        if source == "lal_kitab":
            _ingest_finding(ledger.lk_lines, obj)
        elif source == "mind_and_transits":
            _ingest_finding(ledger.cn_lines, obj)
        return
    if isinstance(obj, (list, tuple)):
        for item in obj:
            _walk(item, ledger, source=source)
        return
    if not isinstance(obj, dict):
        return

    if obj.get("lagna") and not ledger.lagna:
        ledger.lagna = _canon_sign(obj.get("lagna")) or str(obj.get("lagna") or "")
    if obj.get("lagna_lord") and not ledger.lagna_lord:
        ledger.lagna_lord = _canon_planet(obj.get("lagna_lord")) or str(obj.get("lagna_lord") or "")
    if obj.get("primary_house") and not ledger.primary_house:
        ledger.primary_house = _as_int(obj.get("primary_house"))
    if obj.get("primary_house_sign") and not ledger.primary_sign:
        ledger.primary_sign = _canon_sign(obj.get("primary_house_sign"))
    if obj.get("primary_house_lord") and not ledger.primary_lord:
        ledger.primary_lord = _canon_planet(obj.get("primary_house_lord"))
    if obj.get("classical_verdict") and not ledger.verdict:
        ledger.verdict = _trim_line(obj.get("classical_verdict"), 320)
    if obj.get("breakthrough_period") and not ledger.breakthrough:
        ledger.breakthrough = _trim_line(obj.get("breakthrough_period"), 240)
        ledger.windows.append(ledger.breakthrough)
        _add_years(ledger, ledger.breakthrough)
    if obj.get("contingency_rule") and not ledger.judgement:
        status = str(obj.get("status") or "")
        ledger.judgement = _trim_line(
            f"{status}: {obj.get('contingency_rule')}".strip(": "), 240)

    placement = str(obj.get("primary_lord_placement") or "")
    if placement and ledger.primary_lord:
        hm = re.search(r"house\s+(\d{1,2})", placement, re.I)
        sm = re.search(rf"\b({_SIGN_RE})\b", placement, re.I)
        _set_natal(
            ledger, ledger.primary_lord,
            house=_as_int(hm.group(1) if hm else 0),
            sign=sm.group(1) if sm else "",
        )

    audit = obj.get("audit")
    if isinstance(audit, dict) and any(_canon_planet(k) for k in audit):
        for planet, info in audit.items():
            if isinstance(info, dict):
                _ingest_gem(ledger, planet, info)

    if obj.get("gem") and (obj.get("status") or obj.get("planet")):
        _ingest_gem(ledger, str(obj.get("planet") or ""), obj)

    planet = _canon_planet(obj.get("planet") or "")
    house = _as_int(obj.get("house"))
    sign = _canon_sign(obj.get("sign") or "")
    natalish = bool(
        obj.get("gem") or obj.get("owned_houses")
        or str(obj.get("status") or "").upper() in (
            "RECOMMENDED", "AVOID", "MANTRA_ONLY", "STRICTLY_AVOID")
        or obj.get("dignity") or obj.get("primary_lord_dignity")
    )
    if planet and natalish:
        _set_natal(ledger, planet, house=house, sign=sign)
    elif planet and (house or sign) and source in (
            "live_transits", "timing_windows"):
        if house:
            ledger.transit_houses.setdefault(planet, set()).add(house)
        if sign:
            ledger.transit_signs.setdefault(planet, set()).add(sign)

    findings = obj.get("findings")
    if isinstance(findings, list):
        bucket = (ledger.lk_lines if source == "lal_kitab"
                  else ledger.cn_lines if source == "mind_and_transits"
                  else None)
        if bucket is not None:
            for item in findings:
                _ingest_finding(bucket, item)

    for key, val in obj.items():
        if key in ("audit", "findings", "cards"):
            continue
        child_source = source
        if key in ("lal_kitab", "mind_and_transits", "live_transits",
                   "timing_windows", "life_area_confluence"):
            child_source = key
        _walk(val, ledger, source=child_source)


def extract_ledger(results: Optional[dict[str, Any]]) -> Ledger:
    """Flatten tool output into the placements / gems / dates we will enforce."""
    ledger = Ledger()
    _walk(results or {}, ledger)
    if (results or {}).get("lal_kitab") and not ledger.lk_lines:
        _walk((results or {}).get("lal_kitab"), ledger, source="lal_kitab")
    if (results or {}).get("mind_and_transits") and not ledger.cn_lines:
        _walk((results or {}).get("mind_and_transits"), ledger,
              source="mind_and_transits")
    _fill_houses_from_lagna(ledger)
    cy = str(ledger.current_year)
    ledger.this_year_supported = cy in ledger.years and any(
        cy in w for w in ledger.windows) if ledger.years else False
    if not ledger.windows and cy in ledger.years:
        ledger.this_year_supported = True
    return ledger


def grounded_evidence_block(ledger: Ledger) -> str:
    """The only facts the writer is allowed to use."""
    lines = ["ALLOWED FACTS — name nothing that is not on this list."]
    if ledger.lagna:
        lines.append(
            f"Lagna {ledger.lagna}, lagna lord {ledger.lagna_lord or '?'}.")
    if ledger.primary_house:
        lines.append(
            f"Question house {ledger.primary_house} "
            f"({ledger.primary_sign or ledger.house_signs.get(ledger.primary_house, '')}) "
            f"lord {ledger.primary_lord or ledger.house_lords.get(ledger.primary_house, '')}."
        )
    if ledger.natal:
        lines.append("NATAL PLACEMENTS")
        for planet in PLANETS:
            slot = ledger.natal.get(planet)
            if not slot or not (slot.house or slot.sign):
                continue
            owned = ""
            if ledger.owned_houses.get(planet):
                hs = ",".join(str(h) for h in sorted(ledger.owned_houses[planet]))
                owned = f"; lords houses {hs}"
            lines.append(
                f"- {planet}: {slot.sign or '?'} house {slot.house or '?'}{owned}"
            )
    if ledger.gems:
        lines.append("GEMSTONES (wear only RECOMMENDED; never wear AVOID / MANTRA_ONLY)")
        for g in ledger.gems:
            lines.append(f"- {g.label} ({g.planet}): {g.status or 'mentioned'}")
    if ledger.windows or ledger.years:
        years = ", ".join(sorted(ledger.years)) or "none"
        lines.append("TIMING")
        for w in ledger.windows[:4]:
            lines.append(f"- {w}")
        lines.append(f"- Years you may name: {years}")
        if ledger.years and not ledger.this_year_supported:
            lines.append(
                f"- THIS YEAR ({ledger.current_year}) is NOT a strong window. "
                "Do not say the asked event can happen this year."
            )
    if ledger.verdict:
        lines.append(f"VERDICT: {ledger.verdict}")
    if ledger.judgement:
        lines.append(f"CHART JUDGEMENT: {ledger.judgement}")
    if ledger.lk_lines:
        lines.append("LAL KITAB (use at least one sentence, paraphrased)")
        lines.extend(f"- {x}" for x in ledger.lk_lines[:3])
    if ledger.cn_lines:
        lines.append("CHANDRA NAADI (use at least one sentence, paraphrased)")
        lines.extend(f"- {x}" for x in ledger.cn_lines[:3])
    return "\n".join(lines) if len(lines) > 1 else "(no computed facts)"


def _lord_of(ledger: Ledger, planet: str, house: int) -> bool:
    if not house:
        return False
    if ledger.house_lords.get(house) == planet:
        return True
    return house in (ledger.owned_houses.get(planet) or ())


def enforce_grounding(text: str, ledger: Ledger, question: str = "") -> list[str]:
    """Empty list = every named placement / gem / year is in the ledger."""
    body = (text or "").strip()
    if not body:
        return ["empty_answer"]
    problems: list[str] = []
    if _SCAFFOLD.search(body):
        problems.append("used report-style headings instead of short paragraphs")
    if _INTERNAL_STATUS.search(body):
        problems.append("leaked an internal status label")

    for m in _PLANET_SIGN_HOUSE.finditer(body):
        planet, sign, house = _canon_planet(m.group(1)), _canon_sign(m.group(2)), _as_int(m.group(3))
        allowed_h = ledger.allowed_houses(planet)
        allowed_s = ledger.allowed_signs(planet)
        if allowed_h and house not in allowed_h:
            natal = ledger.natal.get(planet)
            where = f"house {natal.house}" if natal and natal.house else "a different house"
            problems.append(f"{planet} is in {where}, not house {house}")
        if allowed_s and sign not in allowed_s:
            natal = ledger.natal.get(planet)
            where = natal.sign if natal and natal.sign else "a different sign"
            problems.append(f"{planet} is in {where}, not {sign}")

    for m in _PLANET_IN_SIGN.finditer(body):
        planet, sign = _canon_planet(m.group(1)), _canon_sign(m.group(2))
        allowed_s = ledger.allowed_signs(planet)
        if allowed_s and sign not in allowed_s:
            natal = ledger.natal.get(planet)
            where = natal.sign if natal and natal.sign else "a different sign"
            problems.append(f"{planet} is in {where}, not {sign}")

    for m in _PLANET_IN_HOUSE.finditer(body):
        planet, house = _canon_planet(m.group(1)), _as_int(m.group(2))
        allowed_h = ledger.allowed_houses(planet)
        if allowed_h and house not in allowed_h:
            natal = ledger.natal.get(planet)
            where = f"house {natal.house}" if natal and natal.house else "a different house"
            problems.append(f"{planet} is in {where}, not house {house}")

    for m in re.finditer(
        rf"\b({_PLANET_RE})\b(?:'s)?(?:\s+\w+){{0,6}}\s+"
        rf"(?:rules|ruling|governs|lord of|owns the|ruler of)\b",
        body, re.I,
    ):
        planet = _canon_planet(m.group(1))
        stop = body.find(".", m.end())
        span = body[m.end(): stop if stop != -1 else m.end() + 140]
        cut = re.search(
            r"\b(?:sits|seated|placed|occupies|is in)\b", span, re.I)
        if cut:
            span = span[:cut.start()]
        for hm in re.finditer(
            r"\b(\d{1,2})(?:st|nd|rd|th)?\s+house\b", span, re.I,
        ):
            house = _as_int(hm.group(1))
            if house and not _lord_of(ledger, planet, house):
                problems.append(f"{planet} does not rule house {house}")
    for m in _HOUSE_RULED_BY.finditer(body):
        house, planet = _as_int(m.group(1)), _canon_planet(m.group(2))
        if house and planet and not _lord_of(ledger, planet, house):
            problems.append(f"{planet} does not rule house {house}")

    for m in _HOUSE_IN_SIGN.finditer(body):
        house, sign = _as_int(m.group(1)), _canon_sign(m.group(2))
        expected = ledger.house_signs.get(house)
        if expected and sign != expected:
            problems.append(f"house {house} is {expected}, not {sign}")

    if ledger.gems:
        low = body.lower()
        for gem in ledger.gems:
            for alias in gem.aliases:
                hit = re.search(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", low)
                if not hit:
                    continue
                idx = hit.start()
                window = low[max(0, idx - 70): idx + len(alias) + 70]
                if gem.status in _AVOID and not _CLEAR_AVOID.search(window):
                    problems.append(
                        f"{gem.label} is {gem.status} — do not offer it as an option")
                    break
                if gem.status in _NO_WEAR and _WEAR.search(window) and not _CLEAR_AVOID.search(window):
                    problems.append(
                        f"do not suggest wearing {gem.label} ({gem.status})")
                    break
        mentioned = [
            alias for alias in _all_gem_aliases()
            if re.search(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", low)
        ]
        known = {a for g in ledger.gems for a in g.aliases} | ledger.gem_aliases
        for alias in mentioned:
            if alias not in known:
                problems.append(f"named gemstone '{alias}' that is not in the evidence")
                break

    if ledger.years:
        for year in _YEAR.findall(body):
            if year not in ledger.years and int(year) != ledger.current_year:
                problems.append(f"year {year} is not in the evidence")
                break

    qlow = (question or "").lower()
    asks_this_year = any(p in qlow for p in (
        "this year", "this yr", str(ledger.current_year)))
    if (asks_this_year and ledger.years and not ledger.this_year_supported
            and _THIS_YEAR_YES.search(body) and not _THIS_YEAR_NO.search(body)):
        problems.append(
            "evidence has no strong window this year — do not say it can happen this year")

    # Deduplicate while keeping order.
    seen: set[str] = set()
    out: list[str] = []
    for p in problems:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out[:6]


def _all_gem_aliases() -> Iterable[str]:
    for aliases in GEM_ALIASES.values():
        yield from aliases


def deterministic_from_ledger(ledger: Ledger, question: str = "") -> str:
    """Second-person answer built only from ledger fields. Never invents."""
    bits: list[str] = []
    qlow = (question or "").lower()
    asked_gem = next(
        (g for g in ledger.gems if any(a in qlow for a in g.aliases)), None)
    gem_q = asked_gem is not None or bool(re.search(
        r"\b(gem|stone|ratna|panna|emerald|wear|sapphire|ruby|pearl|coral|"
        r"diamond|neelam|pukhraj|gomed|lehsunia)\b", qlow))
    recs = list(dict.fromkeys(
        g.label for g in ledger.gems if g.status == "RECOMMENDED"))

    if gem_q and ledger.gems:
        if asked_gem and asked_gem.status == "RECOMMENDED":
            bits.append(
                f"{asked_gem.label} is the stone your chart marks safe to wear "
                f"for {asked_gem.planet}."
            )
        elif asked_gem and asked_gem.status in _NO_WEAR:
            bits.append(
                f"{asked_gem.label} is marked "
                f"{asked_gem.status.replace('_', ' ').title()} on your chart "
                "— do not wear it."
            )
            if recs:
                bits.append("Safe alternatives in this chart: " + ", ".join(recs) + ".")
        elif recs:
            bits.append(
                "Stones this chart marks safe to wear: " + ", ".join(recs) + "."
            )
        avoid = [g.label for g in ledger.gems if g.status in _AVOID]
        if avoid and asked_gem and asked_gem.status == "RECOMMENDED":
            bits.append(
                "Do not wear " + ", ".join(avoid)
                + " — your chart marks those avoid."
            )
    else:
        if ledger.verdict:
            v = _you(ledger.verdict)
            if not re.search(r"\byou\b|\byour\b", v, re.I):
                v = "Your chart shows this: " + v
            bits.append(v)
        elif ledger.primary_house:
            lord = ledger.natal.get(ledger.primary_lord) or Placement()
            bits.append(
                f"Your question sits on house {ledger.primary_house}"
                + (f" ({ledger.primary_sign})" if ledger.primary_sign else "")
                + (f", whose lord {ledger.primary_lord} is in "
                   f"{lord.sign or 'its natal sign'}"
                   f" in house {lord.house or '?'}."
                   if ledger.primary_lord else ".")
            )
        else:
            bits.append(
                "Your chart has a mixed picture on this, and I will stay "
                "with what it actually shows."
            )

        if ledger.breakthrough:
            bits.append(
                f"The strongest window already computed is {ledger.breakthrough}."
            )
        if (question and "this year" in qlow and ledger.years
                and not ledger.this_year_supported):
            bits.append(
                f"That window is not this year ({ledger.current_year}), so I "
                "would not treat this year as the time the chart is backing."
            )

    if ledger.lk_lines:
        bits.append("Lal Kitab on this chart: " + _you(ledger.lk_lines[0]))
    if ledger.cn_lines:
        bits.append("Chandra Naadi on this chart: " + _you(ledger.cn_lines[0]))
    if ledger.judgement and "HEALTHY" not in ledger.judgement.upper():
        bits.append("Chart-judgement note: " + _you(ledger.judgement))

    text = " ".join(bits)
    if not re.search(r"\byou\b|\byour\b|\baap\b", text, re.I):
        text = "Your chart: " + text
    return text


def deterministic_from_results(results: Optional[dict[str, Any]],
                               question: str = "") -> str:
    return deterministic_from_ledger(extract_ledger(results), question)
