"""
vedic_varga_goel.py — Deterministic D7 / D9 / D10 / D30 analysis (Goel, no LLM).

Parses AstroSage || Shodashvarga Table || sign + bhav rows and applies rules from
rules14.md (Saptamsha), rules3.md (Navamsha), rules13.md (Dashamsha),
rules15.md (Trimshamsha).
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
    "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]
SIGN_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}
BENEFICS = frozenset({"Moon", "Mercury", "Jupiter", "Venus"})
MALEFICS = frozenset({"Sun", "Mars", "Saturn", "Rahu", "Ketu"})
NATURAL_BENEFICS = BENEFICS | {"Sun"}  # Sun soft-benefic in Goel child promise
STRONG_DIG = ("exalted", "own_sign", "moolatrikona", "great_friend_sign")
WEAK_DIG = ("debilitated", "enemy_sign")
KENDRA_TRIKONA = (1, 4, 5, 7, 9, 10, 11)
DUSTHANA = (6, 8, 12)

VARGA_ROW = re.compile(
    r"^\s*\d+\s+(Lagna|Saptamamsha|Navamsha|Dashamamsha|Trimshamsha)\s+"
    r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)",
    re.MULTILINE,
)
MALEFIC_LAGNA_LORDS = frozenset({"Mars", "Saturn", "Sun"})
BENEFIC_LAGNA_LORDS = frozenset({"Moon", "Mercury", "Jupiter", "Venus"})
PLANET_KEYS = ["lagna", "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

D7_LAGNA_CHILD_NATURE = {
    "Sun": "heroic, strong-willed, and drawn to leadership",
    "Moon": "gentle, well-behaved, and emotionally close to family",
    "Mars": "proud, courageous, and sometimes hard to manage",
    "Mercury": "clever, talkative, and quick to learn",
    "Jupiter": "wise, respectful, and dharmic in outlook",
    "Venus": "artistic, affectionate, and pleasure-loving",
    "Saturn": "serious, duty-bound, and slower to warm up",
}

D7_HOUSE_MEANING = {
    1: "your desire for children and the poorva punya behind progeny",
    2: "the values and inheritance you pass to children",
    3: "children's courage, siblings among children, and your luck through them",
    4: "happiness FROM children — enjoyment, attachment, and peace at home",
    5: "children's intelligence, creativity, and their own poorva punya",
    6: "health troubles, disputes, or stress linked to children",
    7: "conception, partnership around parenting, and the child's early bonds",
    8: "child longevity, miscarriage risk, and hidden fears around progeny",
    9: "grandchildren, fortune through children, and their higher path",
    10: "children's career, fame, and how much care they give you later",
    11: "gains from children and fulfilment of parental hopes",
    12: "expenses on children and worries that stay private",
}

D9_HOUSE_MEANING = {
    1: "inner temperament toward partnership — how you show up in marriage",
    2: "family values, speech, and financial harmony in the union",
    4: "marital happiness, home comfort, and emotional peace with your partner",
    7: "the marriage itself — partnership quality and staying power",
    8: "mangalya, longevity themes, and deep transformation through marriage",
}

D30_HOUSE_MEANING = {
    1: "fortune vs misfortune — life promise and self-initiated deeds (focal)",
    4: "character, morals, comfort, and hidden emotional tone",
    7: "marriage friction, partnership quality, and union stress",
    8: "chronic trouble, setbacks, and longevity stress (focal)",
    12: "losses, isolation, hospital themes, and self-invited trouble",
}

D10_HOUSE_MEANING = {
    1: "inward career drive — intentions behind all karma this life",
    3: "courage, travel, media, contracts — sudden rise if linked to 10th",
    4: "public acceptance, office base, mass appeal, politics",
    7: "partnerships, corporates, foreigners, business-with-others",
    9: "dharma of profession — luck, law, teaching, government tone",
    10: "main earnings, administration, honour and visible status",
    11: "gains, awards, influential friends — fame house in Dashamsha",
    12: "foreign firms, hospitals, retreat, or behind-the-scenes work",
}

D10_INNER_LORD_IN = {
    1: "a fixed career path — how you initiate action shapes your profession",
    2: "career through speech, family business, food, or stored wealth",
    3: "self-made rise via courage, writing, media, transfers, or contracts",
    4: "land, masses, politics, or careers needing public acceptance",
    5: "sudden turns and subordinates — clever work but boss friction if afflicted",
    6: "service, hospitals, courts, competition, or debt-heavy roles",
    7: "partnerships, corporates, foreigners, or business-with-others",
    8: "sudden gains or losses — crisis work; scandal risk if ethics slip",
    9: "luck, law, teaching, government, or father's influence on work",
    10: "clear professional distinction — honour, command, visible status",
    11: "gains, awards, networks, income from influential friends",
    12: "foreign firms, hospitals, retreat, or behind-the-scenes work",
}

D9_SEVENTH_LORD_IN = {
    1: "marriage colours your whole identity — partner and self are hard to separate",
    2: "union tied to family wealth, speech, and shared values",
    3: "partnership through courage, travel, siblings, or communication",
    4: "home, mother, and emotional roots shape the marriage",
    5: "romance, creativity, and children themes run through partnership",
    6: "service, health, or disputes colour married life — patience needed",
    7: "partnership is central — spouse quality defines the chapter",
    8: "deep transformation, secrecy, or stress around marital longevity",
    9: "luck, dharma, and in-laws influence marriage quality",
    10: "career and public status affect or are affected by the union",
    11: "gains, networks, and social circles through the spouse",
    12: "foreign, private, or retreat themes — love may stay behind the scenes",
}

PLANET_REMEDY = {
    "Sun": "Sundays: sunlight walk, respect elders, keep routine check-ups sensible.",
    "Moon": "Mondays: calm evening, simple food, journal feelings, nurture home peace.",
    "Mars": "Tuesdays: exercise cleanly, channel anger into sport or work — not arguments.",
    "Mercury": "Wednesdays: clear emails, organise papers, study one useful skill.",
    "Jupiter": "Thursdays: modest charity or teaching; avoid risky loans.",
    "Venus": "Fridays: art, kindness, beauty at home — nurture close bonds.",
    "Saturn": "Saturdays: discipline, sleep on time, help someone older; patience pays.",
    "Rahu": "Ground weekly: limit screens and speculation; stick to one practical goal.",
    "Ketu": "Quiet hour daily: meditation, finish an old task, let one habit go.",
}

D10_TENTH_LORD_IN = {
    1: "a self-directed career with public name — learned, visible, and hard to hide",
    2: "income through speech, family business, food, or stored wealth",
    3: "self-made rise through courage, writing, media, transfers, or contracts",
    4: "career tied to land, masses, politics, or public acceptance",
    5: "clever work but unstable bosses — fame through subordinates or creative turns",
    6: "service roles, hospitals, courts, competition, or debt-heavy professions",
    7: "partnerships, corporates, foreigners, or business-with-others",
    8: "sudden rises and falls — research, crisis work, or scandal risk if careless",
    9: "luck, law, teaching, government tone, or father's influence on work",
    10: "clear professional distinction — honour, command, and visible status",
    11: "gains, awards, networks, and income from influential friends",
    12: "foreign firms, hospitals, retreat, or behind-the-scenes work",
}


def _e(s) -> str:
    return html.escape(str(s))


def _ord(n: int) -> str:
    return "%d%s" % (n, {1: "st", 2: "nd", 3: "rd"}.get(n if n < 20 else n % 10, "th"))


def _num_to_sign(n: int) -> str | None:
    if n == 0:
        n = 10  # common AstroSage OCR drop of leading '1'
    if 1 <= n <= 12:
        return SIGNS[n - 1]
    return None


def _sign_idx(sign: str) -> int:
    return SIGNS.index(sign)


def _house_of(sign: str, lagna: str) -> int:
    return (_sign_idx(sign) - _sign_idx(lagna)) % 12 + 1


@dataclass
class VargaChart:
    name: str
    lagna: str
    signs: dict[str, str] = field(default_factory=dict)
    houses: dict[str, int] = field(default_factory=dict)

    def planet_house(self, planet: str) -> int:
        if planet in self.houses and self.houses[planet]:
            return self.houses[planet]
        if planet in self.signs:
            return _house_of(self.signs[planet], self.lagna)
        return 0

    def tenants(self, house: int) -> list[str]:
        return [p for p in PLANET_KEYS if p != "lagna" and self.planet_house(p) == house]

    def house_sign(self, house: int) -> str:
        return SIGNS[(_sign_idx(self.lagna) + house - 1) % 12]

    def house_lord(self, house: int) -> str:
        return SIGN_LORD[self.house_sign(house)]

    def benefic_score(self, house: int) -> int:
        score = 0
        for p in self.tenants(house):
            if p in BENEFICS:
                score += 1
            elif p in MALEFICS:
                score -= 1
        return score

    def saturn_touches(self, houses: set[int]) -> bool:
        if self.planet_house("Saturn") in houses:
            return True
        for h in houses:
            if self.house_lord(h) == "Saturn":
                return True
        return False


def varga_from_divisional(pc: dict, key: str) -> VargaChart | None:
    """Build VargaChart from precomputed divisional signs (PyJHora / chart JSON)."""
    div = pc.get("divisional", {}).get(key)
    if not div:
        return None
    lagna = div.get("Lagna") or div.get("lagna")
    if not lagna:
        return None
    signs: dict[str, str] = {"lagna": lagna}
    for pk in PLANET_KEYS[1:]:
        if pk in div:
            signs[pk] = div[pk]
    return VargaChart(key, lagna, signs, {})


def vargas_from_precompute(pc: dict) -> dict[str, VargaChart]:
    """D1/D7/D9/D10/D30 from precomputed divisional block."""
    out: dict[str, VargaChart] = {}
    for key in ("D1", "D7", "D9", "D10", "D30"):
        vc = varga_from_divisional(pc, key)
        if vc:
            out[key] = vc
    if "D1" not in out:
        meta = pc.get("meta", {})
        lagna = meta.get("lagna_sign") or pc.get("lagna", {}).get("sign")
        if lagna:
            signs = {"lagna": lagna}
            for pname, data in pc.get("planets", {}).items():
                if pname in PLANET_KEYS[1:] and data.get("sign"):
                    signs[pname] = data["sign"]
            out["D1"] = VargaChart("D1", lagna, signs, {})
    return out


def parse_shodashvarga(text: str) -> dict[str, VargaChart]:
    """Return D1/D7/D9/D10/D30 charts from sign + bhav tables."""
    sign_rows: dict[str, list[int]] = {}
    bhav_rows: dict[str, list[int]] = {}
    bhav_start = text.find("Shodashvarga Bhav")
    sign_text = text[:bhav_start] if bhav_start != -1 else text
    bhav_text = text[bhav_start:] if bhav_start != -1 else ""
    for m in VARGA_ROW.finditer(sign_text):
        nums = [int(m.group(i)) for i in range(2, 12)]
        sign_rows[m.group(1)] = nums
    for m in VARGA_ROW.finditer(bhav_text):
        nums = [int(m.group(i)) for i in range(2, 12)]
        bhav_rows[m.group(1)] = nums

    out: dict[str, VargaChart] = {}
    key_map = {
        "Lagna": "D1", "Saptamamsha": "D7", "Navamsha": "D9",
        "Dashamamsha": "D10", "Trimshamsha": "D30",
    }
    for row_name, key in key_map.items():
        if row_name not in sign_rows:
            continue
        signs_raw = sign_rows[row_name]
        lagna = _num_to_sign(signs_raw[0])
        if not lagna:
            continue
        signs = {"lagna": lagna}
        houses: dict[str, int] = {}
        for pk, num in zip(PLANET_KEYS[1:], signs_raw[1:]):
            s = _num_to_sign(num)
            if s:
                signs[pk] = s
        if row_name in bhav_rows:
            bh = bhav_rows[row_name]
            for pk, hnum in zip(PLANET_KEYS[1:], bh[1:]):
                if 1 <= hnum <= 12:
                    houses[pk] = hnum
        out[key] = VargaChart(key, lagna, signs, houses)
    return out


def _verdict_tag(kind: str) -> str:
    labels = {
        "good": ("Good sign", "tag-good"),
        "attention": ("Needs attention", "tag-warn"),
        "hard": ("Challenging", "tag-hard"),
    }
    text, cls = labels.get(kind, ("Mixed", "tag-warn"))
    return f'<span class="{cls}">{text}</span>'


def _dmy(d) -> str:
    return d.strftime("%d %b %Y").lstrip('0')


def _moy(d) -> str:
    return d.strftime("%b %Y")


def _pd(iso: str):
    from datetime import datetime
    return datetime.strptime(iso[:10], "%Y-%m-%d").date()


VIM_ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
VIM_YEARS = {"Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
             "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17}

DOMAIN_TIMING = {
    "children": {"label": "children / conception", "min_age": 21, "max_age": 45, "horizon_years": 12},
    "marriage": {"label": "marriage / partnership", "min_age": 20, "max_age": 50, "horizon_years": 12},
    "career": {"label": "career / status", "min_age": 18, "max_age": 62, "horizon_years": 15},
    "stress": {"label": "stress / adversity", "min_age": 18, "max_age": 70, "horizon_years": 10},
}


def _age_at(vim, d) -> int:
    dob = _pd(vim.pc["meta"]["dob"])
    return max(0, (d - dob).days // 365)


def _age_cap_date(vim, max_age: int):
    from datetime import date
    dob = _pd(vim.pc["meta"]["dob"])
    try:
        return date(dob.year + max_age, dob.month, dob.day)
    except ValueError:
        return date(dob.year + max_age, dob.month, 28)


def _build_md_antardashas(md: dict) -> list[dict]:
    from datetime import timedelta
    md_start = _pd(md["start"])
    md_years = md.get("md_years") or VIM_YEARS[md["md_lord"]]
    md_idx = VIM_ORDER.index(md["md_lord"])
    ads = []
    current = md_start
    for i in range(9):
        ad_lord = VIM_ORDER[(md_idx + i) % 9]
        ad_yrs = VIM_YEARS[ad_lord] * md_years / 120.0
        ad_end = current + timedelta(days=int(ad_yrs * 365.25))
        ads.append({"ad_lord": ad_lord, "start": str(current), "end": str(ad_end)})
        current = ad_end
    return ads


def _domain_timing_cfg(domain: str, female: bool) -> dict:
    cfg = dict(DOMAIN_TIMING[domain])
    if domain == "children" and female:
        cfg["max_age"] = 45
    if domain == "marriage" and female:
        cfg["max_age"] = 48
    return cfg


def _iter_near_antardashas(vim, cfg: dict):
    """Yield (md_lord, ad_dict) for current + future MD antardasas inside horizon and age band."""
    from datetime import date, timedelta
    today = date.today()
    horizon_end = today + timedelta(days=int(cfg["horizon_years"] * 365.25))
    age_cap = _age_cap_date(vim, cfg["max_age"])
    cutoff = min(horizon_end, age_cap)
    for md in getattr(vim, "seq", []):
        md_end = _pd(md["end"])
        if md_end < today:
            continue
        md_start = _pd(md["start"])
        if md_start > cutoff:
            break
        if _age_at(vim, md_start) > cfg["max_age"]:
            break
        for ad in _build_md_antardashas(md):
            ad_start, ad_end = _pd(ad["start"]), _pd(ad["end"])
            if ad_end < today:
                continue
            if ad_start > cutoff:
                continue
            clip_end = min(ad_end, cutoff)
            age_lo = _age_at(vim, max(ad_start, today))
            age_hi = _age_at(vim, clip_end)
            if age_hi < cfg["min_age"]:
                continue
            if age_lo > cfg["max_age"]:
                continue
            yield md["md_lord"], ad, max(ad_start, today), clip_end, age_lo


def _varga_timing_windows(vim, trigger_lords: set[str], domain: str, female: bool = False,
                          limit: int = 4) -> list[str]:
    """Near-term antardasha windows only — age-filtered, no decades-long mahadasa spans."""
    if not vim or not trigger_lords:
        return []
    from datetime import date
    cfg = _domain_timing_cfg(domain, female)
    today = date.today()
    hits: list[tuple] = []
    for md_lord, ad, win_start, win_end, age_lo in _iter_near_antardashas(vim, cfg):
        ad_lord = ad["ad_lord"]
        is_now = win_start <= today < win_end
        ad_hit = ad_lord in trigger_lords
        md_hit = md_lord in trigger_lords
        if not ad_hit and not md_hit:
            continue
        # Future windows must hit the antardasa lord — not a vague mahadasa backdrop.
        if not is_now and not ad_hit:
            continue
        hits.append((0 if is_now else 1, win_start, md_lord, ad_lord, win_start, win_end, age_lo))
    hits.sort(key=lambda x: (x[0], x[1]))
    out: list[str] = []
    seen: set[str] = set()
    got_next = False
    for _, _, md_lord, ad_lord, ws, we, age_lo in hits:
        key = f"{md_lord}-{ad_lord}-{ws}"
        if key in seen:
            continue
        seen.add(key)
        if ws <= today < we:
            label = "Now"
        elif not got_next:
            label, got_next = "Next", True
        else:
            label = "Later"
        out.append(
            f"<strong>{label} (age {age_lo}):</strong> {md_lord}–{ad_lord} antardasa "
            f"({_dmy(ws)} – {_dmy(we)})"
        )
        if len(out) >= limit:
            break
    return out


def _timing_block(vim, trigger_lords: set[str], domain: str, female: bool = False) -> str:
    cfg = _domain_timing_cfg(domain, female)
    label = cfg["label"]
    wins = _varga_timing_windows(vim, trigger_lords, domain, female)
    if not wins:
        return (
            f"<p class='pred'><strong>Timing ({label}):</strong> No biologically plausible "
            f"antardasha for {', '.join(sorted(trigger_lords))} in the next {cfg['horizon_years']} years "
            f"(ages {cfg['min_age']}–{cfg['max_age']}). The chart may still carry the promise — "
            f"timing may sit outside this window or need a supporting lane (Yogini/Jaimini).</p>"
        )
    note = (
        f"Filtered to antardasas in the next {cfg['horizon_years']} years "
        f"and ages {cfg['min_age']}–{cfg['max_age']} — not full-life mahadasa spans."
    )
    return (
        f"<p class='pred'><strong>Timing ({label}):</strong> Goel cross-checks Vimshottari antardasas — "
        f"{' '.join(wins)}. <em>{note}</em></p>"
    )


def _remedy_items(planets: list[str], book_lines: list[str]) -> str:
    items = []
    seen: set[str] = set()
    for line in book_lines:
        if line:
            items.append(f"<li>{_e(line)}</li>")
    for p in planets:
        if p and p in PLANET_REMEDY and p not in seen:
            seen.add(p)
            items.append(f"<li><strong>{p}</strong>: {PLANET_REMEDY[p]}</li>")
    if not items:
        return ""
    return "<ul>" + "".join(items) + "</ul>"


def _d7_remedies(d7: VargaChart, flags: set[str], d1_5th_lord: str) -> str:
    lines = []
    planets = []
    if "saturn_delay" in flags:
        lines.append(
            "Goel: Saturn on Saptamsha lagna/5th/9th delays conception — Saturdays for discipline "
            "and patience; benefic relief on Saturn shortens the wait."
        )
        planets.append("Saturn")
    if "denial" in flags:
        lines.append(
            "Malefic-only Saptamsha lagna — if biology is blocked, benefic support on lagna still "
            "allows child through adoption (Goel exception)."
        )
    if "health_watch" in flags:
        lines.append(
            "6th/8th stress in Saptamsha — schedule preventive care for mother and child; "
            "avoid panic, act early on symptoms."
        )
    if "jupiter_weak" in flags:
        lines.append("Jupiter is karaka for children — strengthen through Thursday charity and respect for teachers.")
        planets.append("Jupiter")
    if "subramanian" in flags or "saturn_delay" in flags:
        lines.append(
            "Classical Santana Tithi (Goel): if Krishna Paksha tithi 7–10 applies, sincere worship "
            "of Lord Subramanian (Murugan) supports conception karma."
        )
    d7_9th_lord = d7.house_lord(9)
    lines.append(
        f"Worship the deity of your Saptamsha 9th-house lord <strong>{d7_9th_lord}</strong> "
        f"for progeny blessings (Goel — 9th in D7 is the God-for-children house)."
    )
    planets.extend([d1_5th_lord, d7.house_lord(1), "Jupiter"])
    body = _remedy_items(planets, lines)
    if not body:
        return ""
    return f"<h2>Saptamsha — remedies (Goel)</h2>{body}"


def _d9_remedies(d9: VargaChart, flags: set[str], female: bool, d1_7th_lord: str) -> str:
    karaka = "Jupiter" if female else "Venus"
    lines = []
    planets = [karaka, d1_7th_lord, d9.house_lord(7), d9.house_lord(1)]
    if "denial" in flags:
        lines.append(
            f"{karaka} alone in Navamsha lagna is a classical denial-or-late-marriage marker — "
            f"strengthen {karaka} and do not rush into mismatched unions."
        )
    if "karaka_dusthana" in flags:
        lines.append(
            f"Marriage karaka {karaka} in a dusthana of Navamsha — weekly habits for {karaka} "
            f"plus honest communication matter more than grand rituals."
        )
    if "h7_stress" in flags:
        lines.append(
            "Navamsha 7th under malefic weight — remedy the 7th lord's planet and avoid "
            "major marital decisions in hostile dasha windows."
        )
        planets.append(d9.house_lord(7))
    if "h4_stress" in flags:
        lines.append(
            "Navamsha 4th stressed — home peace remedies: Mondays for Moon, shared meals, "
            "and small daily kindness with your partner."
        )
        planets.append("Moon")
    if "h8_stress" in flags:
        lines.append(
            "Navamsha 8th under pressure — stay transparent, avoid secrets; Saturn/Moon steadiness "
            "helps mangalya themes."
        )
    lines.append(
        "Goel: Jupiter transit over Navamsha lagna lord supports marriage timing — "
        "triangulate with the Vimshottari windows above."
    )
    body = _remedy_items(planets, lines)
    if not body:
        return ""
    return f"<h2>Navamsha — remedies (Goel)</h2>{body}"


def _d10_remedies(d10: VargaChart, flags: set[str], d1_10th_lord: str) -> str:
    lines = []
    planets = [d10.house_lord(1), d10.house_lord(10), d1_10th_lord]
    if "fall_watch" in flags:
        lines.append(
            "Stressed Dashamsha 8th — Goel warns of sudden loss or humiliation at work if ethics slip; "
            "stay legal, visible, and documented."
        )
    if "service_tone" in flags:
        lines.append(
            "Saturn in a dusthana of Dashamsha — structured employment and duty-bound roles "
            "suit better than risky solo leaps right now."
        )
        planets.append("Saturn")
    if "boss_friction" in flags:
        lines.append(
            "D10 lagna lord in the 5th — clever work but unstable bosses; build skills under "
            "others before betting everything on independence."
        )
    lines.append(
        "Career rise/fall timing (Goel): watch dashas of Dashamsha lagna lord, 10th lord, "
        "and any planet in D10 trik houses — confirmed with Yogini/Jaimini if available."
    )
    body = _remedy_items(planets, lines)
    if not body:
        return ""
    return f"<h2>Dashamsha — remedies (Goel)</h2>{body}"


def _d1_planet_tone(vim, planet: str) -> str:
    if not vim or planet not in getattr(vim, "planets", {}):
        return "attention"
    pl = vim.planets[planet]
    dig, occ = pl.get("dignity", "neutral_sign"), pl.get("house", 1)
    if dig in STRONG_DIG or occ in KENDRA_TRIKONA:
        return "good"
    if dig in WEAK_DIG or occ in DUSTHANA:
        return "hard"
    return "attention"


def _d1_house_tone(vim, house: int) -> str:
    if not vim or house not in getattr(vim, "houses", {}):
        return "attention"
    score = 0
    for p in vim.houses[house].get("tenants", []):
        if p in BENEFICS:
            score += 1
        elif p in MALEFICS:
            score -= 1
    lord_tone = _d1_planet_tone(vim, vim.houses[house]["lord"])
    if score >= 1 and lord_tone != "hard":
        return "good"
    if score <= -1 or lord_tone == "hard":
        return "hard"
    if lord_tone == "good":
        return "good"
    return "attention"


def _score_to_tone(score: int) -> str:
    if score >= 1:
        return "good"
    if score <= -1:
        return "hard"
    return "attention"


def _final_verdict(kind: str, text: str) -> str:
    return f"<p class='pred'>{_verdict_tag(kind)} <strong>Final verdict (D1 + chart):</strong> {text}</p>"


def _synthesize_d7_verdict(vim, d7: VargaChart, d1_5th_lord: str, promise_tone: str, flags: set[str]) -> str:
    d1_5th = _d1_house_tone(vim, 5)
    d1_jup = _d1_planet_tone(vim, "Jupiter")
    d1_ok = d1_5th == "good" or d1_jup == "good"
    d1_weak = d1_5th == "hard" and d1_jup == "hard"

    if promise_tone == "hard" or "denial" in flags:
        if d1_ok:
            return _final_verdict(
                "attention",
                f"Birth chart 5th house and Jupiter look willing, but Saptamsha overrules (Goel): "
                f"progeny is delayed, denied biologically, or comes through adoption — do not read D1 alone as a yes.",
            )
        return _final_verdict(
            "hard",
            "Both birth 5th/Jupiter and Saptamsha are stressed — children are unlikely without deliberate remedial "
            "effort; adoption or accepting a child-free path is the honest read.",
        )
    if "saturn_delay" in flags:
        if d1_ok:
            return _final_verdict(
                "attention",
                f"Children are promised: D1 5th lord {d1_5th_lord} and Jupiter support the birth chart and "
                f"Saptamsha lagna is willing — but Saturn on Saptamsha enforces a wait before conception, not a no.",
            )
        return _final_verdict(
            "attention",
            "Desire for children can manifest, but Saturn delay on Saptamsha plus only mixed D1 support means "
            "late conception or fewer children than hoped — patience through the Saturn-linked windows is required.",
        )
    if promise_tone == "good":
        if d1_ok:
            return _final_verdict(
                "good",
                f"Children are clearly promised: D1 5th lord {d1_5th_lord} and Jupiter back the birth chart, "
                f"and Saptamsha confirms desire and fulfilment — high-confidence progeny when dasha cooperates.",
            )
        return _final_verdict(
            "good",
            "Saptamsha strongly promises children even though D1 5th is only moderate — Goel gives D7 the final "
            "say, and here it delivers a yes.",
        )
    if d1_ok:
        return _final_verdict(
            "attention",
            f"D1 5th lord {d1_5th_lord} supports children, but Saptamsha is mixed — one or two children, or a "
            f"noticeable delay, is more likely than a large family.",
        )
    return _final_verdict(
        "attention",
        "Mixed signals on both charts — a smaller family, stepchildren, or conception only in favourable "
        "antardasas is the balanced verdict.",
    )


def _d9_chart_tone(d9: VargaChart, flags: set[str]) -> str:
    if "denial" in flags:
        return "hard"
    h7, h4 = d9.benefic_score(7), d9.benefic_score(4)
    if h7 <= -1 or ("h7_stress" in flags and h4 <= -1):
        return "hard"
    if h7 >= 1 and h4 >= 0:
        return "good"
    if h7 >= 1 or h4 >= 1:
        return "attention"
    return "attention"


def _synthesize_d9_verdict(vim, d9: VargaChart, d1_7th_lord: str, flags: set[str], female: bool) -> str:
    karaka = "Jupiter" if female else "Venus"
    d1_7 = _d1_house_tone(vim, 7)
    d1_k = _d1_planet_tone(vim, karaka)
    d1_ok = d1_7 == "good" or d1_k == "good"
    d1_weak = d1_7 == "hard" and d1_k == "hard"
    d9_tone = _d9_chart_tone(d9, flags)

    if d1_ok and d9_tone == "good":
        return _final_verdict(
            "good",
            f"Marriage is promised and should mature well — D1 7th lord {d1_7th_lord}, {karaka}, and Navamsha "
            f"7th/4th all cooperate (Goel rules3).",
        )
    if d1_ok and d9_tone == "hard":
        return _final_verdict(
            "attention",
            f"Marriage is likely (D1 7th lord {d1_7th_lord} and {karaka} support union), but Navamsha warns "
            f"the partnership turns strained, distant, or disappointing over time — partner choice and timing matter.",
        )
    if d1_weak and d9_tone == "good":
        return _final_verdict(
            "good",
            "Birth 7th looks hesitant or late, but Navamsha is strong — Goel's rule: marriage can still deliver "
            "lasting happiness when the right dasha opens.",
        )
    if d1_weak and d9_tone == "hard":
        return _final_verdict(
            "hard",
            "Both D1 7th and Navamsha are stressed — late marriage, separation risk, or choosing not to marry "
            "is the cleaner verdict unless remedies and a strong Venus/Jupiter antardasa intervene.",
        )
    if d9_tone == "good":
        return _final_verdict(
            "good",
            f"Navamsha carries the marriage — union is expected to work with steady effort even though D1 7th "
            f"lord {d1_7th_lord} is only mixed.",
        )
    if d9_tone == "hard":
        return _final_verdict(
            "attention",
            f"D1 7th lord {d1_7th_lord} is willing, but Navamsha 7th/4th stress means marriage needs conscious "
            f"work — it will not run on autopilot.",
        )
    return _final_verdict(
        "attention",
        "Marriage is neither denied nor effortless — D1 and Navamsha are mixed; expect a workable union with "
        "patience, not a fairy-tale default.",
    )


def _d10_chart_tone(d10: VargaChart, flags: set[str]) -> str:
    if "fall_watch" in flags:
        return "hard"
    s1, s10 = d10.benefic_score(1), d10.benefic_score(10)
    if s1 >= 0 and s10 >= 0:
        return "good"
    if s1 <= -1 and s10 <= -1:
        return "hard"
    return "attention"


def _synthesize_d10_verdict(vim, d10: VargaChart, d1_10th_lord: str, flags: set[str]) -> str:
    d1_10 = _d1_house_tone(vim, 10)
    d1_tl = _d1_planet_tone(vim, d1_10th_lord)
    d1_ok = d1_10 == "good" or d1_tl == "good"
    d1_weak = d1_10 == "hard" and d1_tl == "hard"
    d10_tone = _d10_chart_tone(d10, flags)

    if d1_ok and d10_tone == "good":
        return _final_verdict(
            "good",
            f"Career rise and public name are promised — D1 10th lord {d1_10th_lord} and Dashamsha lagna/10th "
            f"both support status, income, and visible profession (Goel rules13).",
        )
    if d1_ok and d10_tone == "hard":
        return _final_verdict(
            "attention",
            f"You have professional promise in the birth chart (10th lord {d1_10th_lord}), but Dashamsha warns "
            f"of unstable bosses, scandal risk, or sudden falls — build reputation slowly and stay ethical.",
        )
    if d1_weak and d10_tone == "good":
        return _final_verdict(
            "good",
            "Birth 10th is modest, but Dashamsha is strong — professional karma finds a public channel through "
            "courage, networks, or a later dasha spike even if the early résumé looks ordinary.",
        )
    if d1_weak and d10_tone == "hard":
        return _final_verdict(
            "attention",
            "Both D1 10th and Dashamsha are stressed — structured employment, service roles, or gradual "
            "skill-building suit better than gambling on fame or risky solo leaps.",
        )
    if d10_tone == "good":
        return _final_verdict(
            "good",
            f"Dashamsha confirms how D1 10th lord {d1_10th_lord} shows in the world — career gains come through "
            f"the Dashamsha 10th-lord channel with steady effort.",
        )
    if "boss_friction" in flags:
        return _final_verdict(
            "attention",
            f"Career progresses, but D10 lagna lord in the 5th means clever work under others before independence "
            f"— D1 10th lord {d1_10th_lord} delivers through patience, not one sudden leap.",
        )
    return _final_verdict(
        "attention",
        f"Career is workable but not dazzling on paper — D1 10th lord {d1_10th_lord} and Dashamsha give a "
        f"steady professional path rather than explosive fame.",
    )


def _d30_chart_tone(d30: VargaChart, flags: set[str]) -> str:
    if "misfortune_lagna" in flags or "self_trouble" in flags:
        return "hard"
    if d30.benefic_score(1) >= 1 and d30.benefic_score(8) >= 0:
        return "good"
    if d30.benefic_score(1) <= -1 and d30.benefic_score(8) <= -1:
        return "hard"
    return "attention"


def _synthesize_d30_verdict(
    vim, d30: VargaChart, d1_7th_lord: str, flags: set[str], female: bool, d9: VargaChart | None,
) -> str:
    d30_tone = _d30_chart_tone(d30, flags)
    d1_lagna = _d1_house_tone(vim, 1)
    d1_7 = _d1_house_tone(vim, 7)
    karaka = "Jupiter" if female else "Venus"
    d1_k = _d1_planet_tone(vim, karaka)
    d1_6th_lord = vim.houses[6]["lord"] if vim and 6 in getattr(vim, "houses", {}) else ""
    d1_stress = d1_lagna == "hard" or (d1_6th_lord and _d1_planet_tone(vim, d1_6th_lord) == "hard")

    adversity = ""
    if d30_tone == "good" and not d1_stress:
        adversity = "Life adversity is comparatively low — Trimshamsha is fortunate and D1 lagna is not fighting it."
    elif d30_tone == "hard" and d1_stress:
        adversity = "High friction life chart — unfortunate Trimshamsha plus stressed D1 lagna/6th axis; setbacks and self-invited trouble are recurring themes."
    elif d30_tone == "hard":
        adversity = "Trimshamsha is unfortunate, but D1 lagna is manageable — problems come from circumstances more than self-sabotage."
    elif d30_tone == "good":
        adversity = "Fortunate Trimshamsha softens an otherwise stressed birth lagna — you can recover from hits with effort."
    else:
        adversity = "Mixed fortune and adversity alternate — neither charmed nor cursed; dasha and conduct decide the swing."

    marriage_bit = ""
    if d9 is not None:
        d9_flags: set[str] = set()
        if d9.planet_house(karaka) == 1 and len(d9.tenants(1)) <= 1:
            d9_flags.add("denial")
        if d9.benefic_score(7) <= -1:
            d9_flags.add("h7_stress")
        d9_tone = _d9_chart_tone(d9, d9_flags)
        if "harsh_marriage" in flags and d9_tone == "hard":
            marriage_bit = (
                f" Marriage is a main stress channel: Trimshamsha lagna/7th friction plus weak Navamsha "
                f"(D1 7th lord {d1_7th_lord}) — expect partnership to need heavy remedial attention."
            )
        elif "harsh_marriage" in flags and d9_tone == "good":
            marriage_bit = (
                f" Daily marriage friction is possible in Trimshamsha, but Navamsha is strong — union can hold "
                f"if D1 7th lord {d1_7th_lord} and {karaka} get supportive dashas."
            )
        elif d9_tone == "good" and d1_7 == "good":
            marriage_bit = f" Marriage quality is supported on D1, Navamsha, and Trimshamsha — partnership is not the main misfortune lane."
        elif d9_tone == "hard":
            marriage_bit = (
                f" Navamsha stresses marriage despite mixed Trimshamsha — long-term union quality stays guarded "
                f"even if wedding happens."
            )
        else:
            marriage_bit = (
                f" Marriage sits in the middle band — D1 7th lord {d1_7th_lord} and {karaka} must be strengthened "
                f"in hostile sub-periods."
            )
    elif "harsh_marriage" in flags:
        marriage_bit = (
            f" Trimshamsha flags partnership friction (D1 7th lord {d1_7th_lord}) — treat love as a remedial area, "
            f"not a background theme."
        )

    kind = "good" if d30_tone == "good" and not d1_stress else (
        "hard" if d30_tone == "hard" and d1_stress else "attention"
    )
    return _final_verdict(kind, adversity + marriage_bit)


def _child_houses(d7: VargaChart) -> list[int]:
    odd = _sign_idx(d7.lagna) % 2 == 0  # Aries=0 even index → odd sign
    if odd:
        seq = [5, 7, 9, 11, 1, 3, 4, 6, 8, 10, 12]
    else:
        seq = [9, 7, 5, 3, 1, 11, 10, 8, 6, 4, 2]
    return seq


def _count_children_hint(d7: VargaChart) -> tuple[str, str]:
    seq = _child_houses(d7)
    count = 0
    stop_reason = ""
    for h in seq:
        tenants = d7.tenants(h)
        lord = d7.house_lord(h)
        if "Ketu" in tenants and len(tenants) == 1:
            count += 1
            stop_reason = f"Ketu alone in the {_ord(h)} child-house suggests this is the last child."
            break
        if "Ketu" in tenants and lord == "Ketu" and len(tenants) <= 2:
            count += 1
            stop_reason = f"Ketu with the child-house lord in the {_ord(h)} house caps the line."
            break
        if tenants or d7.benefic_score(h) >= 0:
            count += 1
        if count >= 4:
            break
    if count == 0:
        return "attention", "Child-house sequence is weak — promise may be delayed rather than absent."
    if count >= 3:
        return "good", f"Up to {count} child-houses look active before the sequence stops — several children are plausible."
    return "attention", f"About {count} child-house{'s' if count != 1 else ''} look strongly marked — a smaller family is the cleaner read."


def analyze_d7(d7: VargaChart, d1_lagna: str, d1_5th_lord: str, female: bool, vim=None) -> str:
    parts = []
    flags: set[str] = set()
    ll = d7.house_lord(1)
    lagna_score = d7.benefic_score(1)
    if lagna_score >= 1:
        promise_tone = "good"
        promise = "Saptamsha lagna is supported — the desire for children is present and efforts can bear fruit."
    elif lagna_score <= -1:
        promise_tone = "hard"
        flags.add("denial")
        promise = "Malefic weight on Saptamsha lagna — delay, denial, or adoption themes need honest consideration."
    else:
        promise_tone = "attention"
        promise = "Saptamsha lagna is mixed — children are not denied outright, but timing may ask for patience."

    parts.append(f"<p class='pred'>{_verdict_tag(promise_tone)} <strong>Promise of children:</strong> {promise}</p>")

    if d7.saturn_touches({1, 5, 9}):
        relief = any(d7.benefic_score(h) > 0 for h in (1, 5, 9))
        tag = "attention" if relief else "hard"
        flags.add("saturn_delay")
        if not relief:
            flags.add("subramanian")
        parts.append(
            f"<p class='pred'>{_verdict_tag(tag)} <strong>Delay factor:</strong> Saturn touches Saptamsha lagna, "
            f"5th, or 9th — Goel reads this as a wait before conception; benefic relief shortens it, malefic-only stretches it.</p>"
        )

    h4 = d7.benefic_score(4)
    if h4 >= 1:
        parts.append(
            f"<p class='pred'>{_verdict_tag('good')} <strong>Happiness from children:</strong> "
            f"The 4th from Saptamsha lagna is supported — you are likely to enjoy your children and feel proud of them.</p>"
        )
    elif h4 <= -1:
        parts.append(
            f"<p class='pred'>{_verdict_tag('hard')} <strong>Happiness from children:</strong> "
            f"Stress on the 4th from Saptamsha — joy may come, but not without worry, distance, or emotional cost.</p>"
        )
    else:
        parts.append(
            f"<p class='pred'>{_verdict_tag('attention')} <strong>Happiness from children:</strong> "
            f"The 4th is neutral — happiness depends more on how you nurture the bond than on the chart alone.</p>"
        )

    cnt_v, cnt_txt = _count_children_hint(d7)
    parts.append(f"<p class='pred'>{_verdict_tag(cnt_v)} <strong>Number of children:</strong> {cnt_txt}</p>")

    first_h = _child_houses(d7)[0]
    first_lord = d7.house_lord(first_h)
    first_tenants = d7.tenants(first_h)
    gender_hint = "mixed"
    if first_lord in ("Sun", "Mars", "Jupiter", "Rahu") or d7.house_sign(first_h) in (
        "Aries", "Cancer", "Leo", "Libra", "Scorpio", "Sagittarius"
    ):
        gender_hint = "male-leaning"
    elif first_lord in ("Moon", "Venus", "Ketu") or d7.house_sign(first_h) in (
        "Taurus", "Virgo", "Capricorn", "Aquarius"
    ):
        gender_hint = "female-leaning"
    parts.append(
        f"<p class='pred'>{_verdict_tag('attention')} <strong>First child (indication):</strong> "
        f"Child-house {_ord(first_h)} is ruled by {first_lord}"
        f"{(' with ' + ', '.join(first_tenants)) if first_tenants else ''} — a {gender_hint} indication; confirm after birth.</p>"
    )

    parts.append(
        f"<p class='pred'>{_verdict_tag('good')} <strong>Nature of children:</strong> "
        f"Saptamsha lagna lord {ll} suggests children who are {D7_LAGNA_CHILD_NATURE.get(ll, 'mixed in temperament')}.</p>"
    )

    h10 = d7.benefic_score(10)
    if h10 >= 1:
        parts.append(
            f"<p class='pred'>{_verdict_tag('good')} <strong>Children's career & your care later:</strong> "
            f"A strong 10th from Saptamsha — children may do well professionally and remember you kindly.</p>"
        )
    elif h10 <= -1:
        parts.append(
            f"<p class='pred'>{_verdict_tag('attention')} <strong>Children's career & your care later:</strong> "
            f"A stressed 10th — children may succeed on their own terms but stay busy with their own lives.</p>"
        )

    jup_h = d7.planet_house("Jupiter")
    if jup_h in (1, 5, 9):
        parts.append(
            f"<p class='pred'>{_verdict_tag('good')} <strong>Devotion & respect:</strong> "
            f"Jupiter in the {_ord(jup_h)} house of Saptamsha supports respect between you and your children.</p>"
        )
    elif jup_h in (6, 8, 12):
        flags.add("jupiter_weak")
        parts.append(
            f"<p class='pred'>{_verdict_tag('attention')} <strong>Devotion & respect:</strong> "
            f"Jupiter in a dusthana of Saptamsha — bond is karmic; patience and fairness matter more than control.</p>"
        )

    h6 = d7.benefic_score(6)
    h8 = d7.benefic_score(8)
    if h6 <= -1 or h8 <= -1:
        flags.add("health_watch")
        parts.append(
            f"<p class='pred'>{_verdict_tag('attention')} <strong>Child health watch:</strong> "
            f"6th or 8th from Saptamsha carries malefic weight — schedule prevention, not panic.</p>"
        )

    h9 = d7.benefic_score(9)
    if h9 >= 1:
        parts.append(
            f"<p class='pred'>{_verdict_tag('good')} <strong>Grandchildren:</strong> "
            f"The 9th from Saptamsha is supported — fortune through grandchildren is a live theme.</p>"
        )

    h2 = d7.benefic_score(2)
    parts.append(
        f"<p class='pred'>{_verdict_tag('good' if h2 >= 0 else 'attention')} <strong>Values you pass on:</strong> "
        f"The 2nd from Saptamsha ({D7_HOUSE_MEANING[2][:50]}…) is "
        f"{'supported' if h2 >= 0 else 'under stress'}.</p>"
    )

    if d7.planet_house("Jupiter") == 5:
        parts.append(
            f"<p class='pred'>{_verdict_tag('good')} <strong>Child's progress:</strong> "
            f"Jupiter in the 5th from the first child-house — a classical mark of auspicious progress for progeny.</p>"
        )

    parts.append(_synthesize_d7_verdict(vim, d7, d1_5th_lord, promise_tone, flags))
    triggers = {d1_5th_lord, "Jupiter", ll, d7.house_lord(5), d7.house_lord(9)}
    triggers.discard(None)
    parts.append(_timing_block(vim, triggers, "children", female))
    parts.append(_d7_remedies(d7, flags, d1_5th_lord))
    return "".join(parts)


def analyze_d9(d9: VargaChart, female: bool, d1_7th_lord: str, vim=None) -> str:
    parts = []
    flags: set[str] = set()
    karaka = "Jupiter" if female else "Venus"
    k_h = d9.planet_house(karaka)
    k_sign = d9.signs.get(karaka, "?")

    lagna_v = "good" if d9.benefic_score(1) >= 0 else ("hard" if d9.benefic_score(1) <= -1 else "attention")
    parts.append(
        f"<p class='pred'>{_verdict_tag(lagna_v)} <strong>Desire for marriage:</strong> "
        f"Navamsha lagna in <strong>{d9.lagna}</strong> "
        f"{'welcomes partnership' if lagna_v == 'good' else 'shows hesitation or heavy karma around partnership' if lagna_v == 'hard' else 'is open but cautious'}.</p>"
    )

    h7s = d9.benefic_score(7)
    if h7s >= 1:
        parts.append(
            f"<p class='pred'>{_verdict_tag('good')} <strong>Marriage promise:</strong> "
            f"The 7th house of Navamsha is supported — partnership is promised to mature, not merely begin.</p>"
        )
    elif h7s <= -1:
        flags.add("h7_stress")
        parts.append(
            f"<p class='pred'>{_verdict_tag('hard')} <strong>Marriage promise:</strong> "
            f"Malefic pressure on Navamsha 7th — chronic stress, separation risk, or a very late union is possible.</p>"
        )
    else:
        parts.append(
            f"<p class='pred'>{_verdict_tag('attention')} <strong>Marriage promise:</strong> "
            f"Navamsha 7th is mixed — marriage can work, but it will not run on autopilot.</p>"
        )

    h4s = d9.benefic_score(4)
    if h4s >= 1:
        parts.append(
            f"<p class='pred'>{_verdict_tag('good')} <strong>Happiness in marriage:</strong> "
            f"Navamsha 4th is strong — home life and emotional peace with your partner can be genuinely good.</p>"
        )
    elif h4s <= -1:
        flags.add("h4_stress")
        parts.append(
            f"<p class='pred'>{_verdict_tag('hard')} <strong>Happiness in marriage:</strong> "
            f"Navamsha 4th is stressed — comfort at home may be the hardest part to sustain.</p>"
        )
    else:
        parts.append(
            f"<p class='pred'>{_verdict_tag('attention')} <strong>Happiness in marriage:</strong> "
            f"Navamsha 4th is neutral — happiness grows through daily kindness, not grand gestures alone.</p>"
        )

    if k_h == 1 and len(d9.tenants(1)) <= 1:
        flags.add("denial")
        parts.append(
            f"<p class='pred'>{_verdict_tag('hard')} <strong>Denial / delay flag:</strong> "
            f"{karaka} alone in Navamsha lagna is a classical denial-or-late-marriage marker — check remedies and timing.</p>"
        )
    elif k_h in (6, 8, 12):
        flags.add("karaka_dusthana")
        parts.append(
            f"<p class='pred'>{_verdict_tag('attention')} <strong>Marriage karaka:</strong> "
            f"{karaka} in the {_ord(k_h)} house of Navamsha ({k_sign}) — love is karmic; quality depends on dignity and aspects.</p>"
        )
    else:
        parts.append(
            f"<p class='pred'>{_verdict_tag('good' if k_h in (4, 7, 11) else 'attention')} <strong>Marriage karaka:</strong> "
            f"{karaka} in the {_ord(k_h)} house of Navamsha — long-term tone is {'supportive' if k_h in (4, 7, 11) else 'workable with effort'}.</p>"
        )

    ll7 = d9.house_lord(7)
    ll7_h = d9.planet_house(ll7)
    parts.append(
        f"<p class='pred'>{_verdict_tag('attention')} <strong>7th lord in Navamsha:</strong> "
        f"{ll7} rules the marriage house and sits in the {_ord(ll7_h)} house — "
        f"{D9_SEVENTH_LORD_IN.get(ll7_h, 'partnership runs through that life area')}.</p>"
    )

    if d9.planet_house("Rahu") == 7 or d9.planet_house("Ketu") == 7:
        parts.append(
            f"<p class='pred'>{_verdict_tag('attention')} <strong>Foreign / unconventional union:</strong> "
            f"Rahu or Ketu in Navamsha 7th — partner may come from a different background or path.</p>"
        )

    h2s = d9.benefic_score(2)
    parts.append(
        f"<p class='pred'>{_verdict_tag('good' if h2s >= 0 else 'attention')} <strong>Values & stability:</strong> "
        f"Navamsha 2nd (sanskar) is {'supported — stabilising values help marriage last' if h2s >= 0 else 'stressed — values mismatch can erode permanence'}.</p>"
    )

    h8s = d9.benefic_score(8)
    if h8s <= -1:
        flags.add("h8_stress")
        parts.append(
            f"<p class='pred'>{_verdict_tag('attention')} <strong>Mangalya / longevity themes:</strong> "
            f"Navamsha 8th under malefic weight — deep transformation or stress around marital longevity.</p>"
        )

    mh, vh = d9.planet_house("Mars"), d9.planet_house("Venus")
    if mh and vh and (mh == vh or abs(mh - vh) == 6):
        parts.append(
            f"<p class='pred'>{_verdict_tag('attention')} <strong>Passion level:</strong> "
            f"Mars and Venus linked in Navamsha — high romantic/sexual charge; channel it with honesty.</p>"
        )

    parts.append(_synthesize_d9_verdict(vim, d9, d1_7th_lord, flags, female))
    triggers = {karaka, d1_7th_lord, d9.house_lord(7), d9.house_lord(1), "Venus", "Jupiter"}
    triggers.discard(None)
    parts.append(_timing_block(vim, triggers, "marriage", female))
    parts.append(_d9_remedies(d9, flags, female, d1_7th_lord))
    return "".join(parts)


def analyze_d10(d10: VargaChart, d1_10th_lord: str, d1_lagna: str, vim=None) -> str:
    parts = []
    flags: set[str] = set()
    ll = d10.house_lord(1)
    ll_h = d10.planet_house(ll)
    t10_lord = d10.house_lord(10)
    t10_h = d10.planet_house(t10_lord)

    if ll_h == 5:
        flags.add("boss_friction")
    parts.append(
        f"<p class='pred'>{_verdict_tag('good' if d10.benefic_score(1) >= 0 else 'attention')} "
        f"<strong>Inner career drive (D10 lagna):</strong> Lagna in <strong>{d10.lagna}</strong>, "
        f"lord {ll} in the {_ord(ll_h)} house — {D10_INNER_LORD_IN.get(ll_h, 'your inner work style follows that house')}.</p>"
    )

    parts.append(
        f"<p class='pred'>{_verdict_tag('good' if d10.benefic_score(10) >= 0 else 'attention')} "
        f"<strong>Public profession (D10 10th):</strong> 10th lord {t10_lord} sits in the {_ord(t10_h)} house — "
        f"{D10_TENTH_LORD_IN.get(t10_h, 'your public face follows that channel')}.</p>"
    )

    cap_tenants = [p for p in PLANET_KEYS if p != "lagna" and d10.signs.get(p) == "Capricorn"]
    if cap_tenants or d10.lagna == "Capricorn":
        parts.append(
            f"<p class='pred'>{_verdict_tag('good')} <strong>Status amplifier:</strong> "
            f"Capricorn emphasis in Dashamsha lifts career weight — duty, structure, and endurance matter.</p>"
        )

    pp = [p for p in ("Sun", "Moon", "Mars", "Rahu") if d10.planet_house(p) in (1, 10)]
    if len(pp) >= 2:
        parts.append(
            f"<p class='pred'>{_verdict_tag('good')} <strong>Independence:</strong> "
            f"{', '.join(pp)} touch D10 lagna or 10th — self-employment or high autonomy is plausible.</p>"
        )
    elif d10.planet_house("Saturn") in (6, 8, 12):
        flags.add("service_tone")
        parts.append(
            f"<p class='pred'>{_verdict_tag('attention')} <strong>Service tone:</strong> "
            f"Saturn in a dusthana of Dashamsha — structured employment or duty-bound roles suit better than risky solo leaps.</p>"
        )

    h11 = d10.benefic_score(11)
    if h11 >= 1:
        parts.append(
            f"<p class='pred'>{_verdict_tag('good')} <strong>Fame & gains:</strong> "
            f"Dashamsha 11th is supported — awards, networks, and income from reputation are live themes.</p>"
        )

    h3_link = d10.planet_house(d10.house_lord(3)) in (10,) or d10.planet_house(d10.house_lord(10)) == 3
    if h3_link or d10.planet_house("Mars") in (3, 10):
        parts.append(
            f"<p class='pred'>{_verdict_tag('good')} <strong>Sudden rise potential:</strong> "
            f"3rd–10th link in Dashamsha — courage, transfers, or media can spike your name quickly.</p>"
        )

    h4 = d10.benefic_score(4)
    if h4 >= 1:
        parts.append(
            f"<p class='pred'>{_verdict_tag('good')} <strong>Public acceptance:</strong> "
            f"Dashamsha 4th is strong — masses, politics, or land-linked career can bring popularity.</p>"
        )

    h8 = d10.benefic_score(8)
    if h8 <= -1:
        flags.add("fall_watch")
        parts.append(
            f"<p class='pred'>{_verdict_tag('hard')} <strong>Fall / scandal watch:</strong> "
            f"Stressed Dashamsha 8th — sudden loss or humiliation at work if ethics slip; stay legal and visible.</p>"
        )

    h9 = d10.benefic_score(9)
    if h9 >= 1:
        parts.append(
            f"<p class='pred'>{_verdict_tag('good')} <strong>Dharma of profession:</strong> "
            f"Dashamsha 9th supported — law, teaching, government, or father's influence helps career.</p>"
        )

    jup_h = d10.planet_house("Jupiter")
    mer_h = d10.planet_house("Mercury")
    if jup_h in (1, 10) or mer_h in (1, 10):
        parts.append(
            f"<p class='pred'>{_verdict_tag('good')} <strong>Knowledge work:</strong> "
            f"Jupiter or Mercury on Dashamsha lagna/10th — teaching, finance, writing, or advisory roles fit well.</p>"
        )

    parts.append(_synthesize_d10_verdict(vim, d10, d1_10th_lord, flags))
    triggers = {ll, t10_lord, d1_10th_lord, "Sun", "Saturn"}
    for p in ("Sun", "Moon", "Mars", "Saturn", "Rahu"):
        if d10.planet_house(p) in (6, 8, 12):
            triggers.add(p)
    triggers.discard(None)
    parts.append(_timing_block(vim, triggers, "career"))
    parts.append(_d10_remedies(d10, flags, d1_10th_lord))
    return "".join(parts)


def _d30_remedies(d30: VargaChart, flags: set[str], d1_6th_lord: str, d1_8th_lord: str) -> str:
    lines = []
    planets = [d30.house_lord(1), d30.house_lord(8), d1_6th_lord, d1_8th_lord]
    if "misfortune_lagna" in flags or "self_trouble" in flags:
        lines.append(
            "Goel: afflicted Trimshamsha lagna lord invites self-created trouble — weekly habits for "
            "that planet plus honest accountability matter more than fear-based rituals."
        )
        planets.append(d30.house_lord(1))
    if "harsh_marriage" in flags:
        lines.append(
            "Malefic weight on Trimshamsha lagna/7th — marriage needs patience and fair speech; "
            "strengthen Venus/Jupiter (karakas) and avoid major union decisions in hostile antardasas."
        )
        planets.extend(["Venus", "Jupiter"])
    if "h8_stress" in flags:
        lines.append(
            "Trimshamsha 8th stressed — Goel uses D30 8th lord and D1 6th/8th lords for remedial focus; "
            "prevention and legal/ethical conduct reduce relapse tone."
        )
        planets.extend([d30.house_lord(8), d1_6th_lord, d1_8th_lord])
    lines.append(
        f"Perform simple remedies for the Trimshamsha lords of your birth <strong>6th lord ({d1_6th_lord})</strong> "
        f"and <strong>8th lord ({d1_8th_lord})</strong> during their Vimshottari antardasas (Goel Ch.04)."
    )
    body = _remedy_items(planets, lines)
    if not body:
        return ""
    return f"<h2>Trimshamsha — remedies (Goel)</h2>{body}"


def analyze_d30(
    d30: VargaChart,
    d1_lagna: str,
    d1_7th_lord: str,
    d1_6th_lord: str,
    d1_8th_lord: str,
    female: bool,
    vim=None,
    d9: VargaChart | None = None,
) -> str:
    parts = []
    flags: set[str] = set()
    ll = d30.house_lord(1)
    ll_h = d30.planet_house(ll)
    lagna_score = d30.benefic_score(1)
    lagna_ll = SIGN_LORD[d30.lagna]

    if lagna_score >= 1 and lagna_ll in BENEFIC_LAGNA_LORDS:
        parts.append(
            f"<p class='pred'>{_verdict_tag('good')} <strong>Fortune tone:</strong> "
            f"Trimshamsha lagna in <strong>{d30.lagna}</strong> is supported — Goel reads this as a "
            f"<em>fortunate</em> Trishamsha; life problems are fewer and easier to manage.</p>"
        )
    elif lagna_score <= -1 and lagna_ll in MALEFIC_LAGNA_LORDS:
        flags.add("misfortune_lagna")
        parts.append(
            f"<p class='pred'>{_verdict_tag('hard')} <strong>Misfortune tone:</strong> "
            f"Malefic sign <strong>{d30.lagna}</strong> on Trimshamsha lagna with malefic weight — "
            f"Goel's <em>arista phalam</em> chart; adversity and friction are live themes.</p>"
        )
    else:
        parts.append(
            f"<p class='pred'>{_verdict_tag('attention')} <strong>Mixed fortune tone:</strong> "
            f"Trimshamsha lagna in <strong>{d30.lagna}</strong> has both support and stress — "
            f"fortune and adversity alternate through life.</p>"
        )

    ll_score = d30.benefic_score(ll_h) if ll_h else 0
    if ll_score >= 0 and lagna_score >= 0:
        parts.append(
            f"<p class='pred'>{_verdict_tag('good')} <strong>Lagna lord action:</strong> "
            f"{ll} in the {_ord(ll_h)} house of Trimshamsha can fulfill the promise — "
            f"you are less likely to invite trouble by your own deeds.</p>"
        )
    elif ll_score <= -1 and lagna_score <= -1:
        flags.add("self_trouble")
        parts.append(
            f"<p class='pred'>{_verdict_tag('hard')} <strong>Lagna lord action:</strong> "
            f"{ll} afflicted in Trimshamsha — Goel warns you may <em>increase</em> misfortune "
            f"through your own choices; slow down in hostile sub-periods.</p>"
        )
    else:
        parts.append(
            f"<p class='pred'>{_verdict_tag('attention')} <strong>Lagna lord action:</strong> "
            f"{ll} in the {_ord(ll_h)} house — mixed ability to convert adversity into learning.</p>"
        )

    h8 = d30.benefic_score(8)
    l8 = d30.house_lord(8)
    if h8 <= -1:
        flags.add("h8_stress")
        parts.append(
            f"<p class='pred'>{_verdict_tag('hard')} <strong>8th house (focal):</strong> "
            f"Trimshamsha 8th under malefic weight — chronic setbacks, hidden fears, or relapse tone; "
            f"8th lord <strong>{l8}</strong> needs remedial attention.</p>"
        )
    elif h8 >= 1:
        parts.append(
            f"<p class='pred'>{_verdict_tag('good')} <strong>8th house (focal):</strong> "
            f"Trimshamsha 8th is supported — sudden trouble is easier to absorb and recover from.</p>"
        )
    else:
        parts.append(
            f"<p class='pred'>{_verdict_tag('attention')} <strong>8th house (focal):</strong> "
            f"Trimshamsha 8th is neutral — outcomes depend on dasha lords and conduct.</p>"
        )

    moon_h = d30.planet_house("Moon")
    if moon_h in (6, 8, 12):
        flags.add("moon_stress")
        parts.append(
            f"<p class='pred'>{_verdict_tag('attention')} <strong>Moon (focal):</strong> "
            f"Moon in the {_ord(moon_h)} house of Trimshamsha — emotional stress colours how you "
            f"handle adversity; mind-care is part of the remedy.</p>"
        )
    elif moon_h in (1, 4, 7, 10):
        parts.append(
            f"<p class='pred'>{_verdict_tag('good')} <strong>Moon (focal):</strong> "
            f"Moon in the {_ord(moon_h)} house of Trimshamsha — emotional resilience is workable.</p>"
        )

    h7 = d30.benefic_score(7)
    if h7 <= -1 or (lagna_ll in MALEFIC_LAGNA_LORDS and lagna_score <= 0):
        flags.add("harsh_marriage")
        parts.append(
            f"<p class='pred'>{_verdict_tag('attention')} <strong>Marriage quality (D30):</strong> "
            f"Malefic influence on Trimshamsha lagna/7th — Goel ties this to partnership friction and "
            f"daily strain in the union.</p>"
        )
    elif h7 >= 1:
        parts.append(
            f"<p class='pred'>{_verdict_tag('good')} <strong>Marriage quality (D30):</strong> "
            f"Trimshamsha 7th is supported — union is not the main misfortune channel.</p>"
        )

    h4 = d30.benefic_score(4)
    if h4 <= -1:
        parts.append(
            f"<p class='pred'>{_verdict_tag('attention')} <strong>Character / comfort (D30 4th):</strong> "
            f"Stressed 4th in Trimshamsha — morals and home peace need conscious upkeep (Goel).</p>"
        )

    if d30.planet_house("Saturn") == 1 and d1_lagna in ("Capricorn", "Aquarius"):
        parts.append(
            f"<p class='pred'>{_verdict_tag('attention')} <strong>Early union flag:</strong> "
            f"Saturn in Trimshamsha lagna with Saturn-linked D1 lagna — Goel (rules3) notes "
            f"early marriage is possible, but quality may need maturity.</p>"
        )

    if d30.tenants(1) and lagna_ll in MALEFIC_LAGNA_LORDS:
        malefic_on_lagna = [p for p in d30.tenants(1) if p in MALEFICS]
        if malefic_on_lagna:
            flags.add("harsh_marriage")
            parts.append(
                f"<p class='pred'>{_verdict_tag('hard')} <strong>Lagna occupant:</strong> "
                f"{', '.join(malefic_on_lagna)} in Trimshamsha lagna — same planet stressing D1 lagna "
                f"axis is a classic misfortune marker (Goel).</p>"
            )

    parts.append(_synthesize_d30_verdict(vim, d30, d1_7th_lord, flags, female, d9))

    stress_triggers = {ll, l8, d1_6th_lord, d1_8th_lord, SIGN_LORD.get(d30.signs.get("Moon", ""), "")}
    marriage_triggers = {d1_7th_lord, ll, l8, "Venus", "Jupiter"}
    stress_triggers.discard(None)
    marriage_triggers.discard(None)
    parts.append(_timing_block(vim, stress_triggers, "stress"))
    parts.append(_timing_block(vim, marriage_triggers, "marriage", female))
    parts.append(_d30_remedies(d30, flags, d1_6th_lord, d1_8th_lord))
    return "".join(parts)


def varga_facts_table(chart: VargaChart, title: str) -> str:
    rows = []
    house_sets = {
        "D7": (1, 2, 4, 5, 6, 8, 9, 10, 11),
        "D9": (1, 2, 4, 7, 8),
        "D10": (1, 3, 4, 7, 9, 10, 11, 12),
        "D30": (1, 4, 7, 8, 12),
    }
    meaning_map = {
        "D7": D7_HOUSE_MEANING, "D9": D9_HOUSE_MEANING,
        "D10": D10_HOUSE_MEANING, "D30": D30_HOUSE_MEANING,
    }
    themes = meaning_map.get(chart.name, {})
    for h in house_sets.get(chart.name, (1, 4, 5, 7, 10)):
        tenants = ", ".join(chart.tenants(h)) or "—"
        meaning = themes.get(h, f"{_ord(h)}-house theme in {chart.name}")
        rows.append(
            f"<tr><td>{_ord(h)}</td><td>{chart.house_sign(h)}</td><td>{chart.house_lord(h)}</td>"
            f"<td>{tenants}</td><td>{_e(meaning[:70])}</td></tr>"
        )
    return (
        f"<h2>{_e(title)} — key houses</h2>"
        f"<table class='simple'><tr><th>House</th><th>Sign</th><th>Lord</th><th>Planets</th><th>Theme</th></tr>"
        + "".join(rows) + "</table>"
    )
