"""Crisp daily summary built from the day's confluence of signals.

The daily guide computes a lot (Tarabala, Chandrabala, Moon gochar, Ashtakavarga,
dasha, Jaimini, muhurat). Readers care about five things: how is today, which
parts of life are helped or strained, what to do, what to avoid, and when.

This module turns the confluence into exactly that, with no model call (the
daily reading is opened every morning, so it must be instant and free to run):

* every available signal votes +1 (supportive), 0 (neutral) or -1 (strained);
* the votes give a 1-10 day strength, "n of m checks agree", and the chips that
  show *why* the day reads the way it does;
* four life tiles (Work, Money, People, Mind) are each judged from the signals
  that actually speak to that area;
* the Do / Don't lists are trimmed to one actionable line each.

Everything here is pure: reading dict in, small dict out.
"""
from __future__ import annotations

import re
from typing import Any, Optional

try:
    from ashtakavarga_analysis import HOUSE_LIFE_THEME
except Exception:  # noqa: BLE001
    HOUSE_LIFE_THEME = {}

UP, MIXED, DOWN = "up", "mixed", "down"
TONE_WORD = {UP: "Good", MIXED: "Mixed", DOWN: "Careful"}

# Sources whose Do/Don't lines only repeat what the lucky-colour row already says.
_REDUNDANT_SRC = ("rules40/41",)
# Preferred order for the short Do / Don't lists (most chart-specific first).
_SRC_ORDER = ("tarabala", "chandrabal", "gochar", "pratyantar", "antardasha",
              "transit nakshatra", "moonology", "bhardwaj")


def _g(d: Any, *path: str, default: Any = None) -> Any:
    for p in path:
        if not isinstance(d, dict):
            return default
        d = d.get(p)
        if d is None:
            return default
    return d


def _first_sentence(text: str, limit: int = 120) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if not text:
        return ""
    m = re.match(r"(.+?[.!?])(\s|$)", text)
    s = m.group(1) if m else text
    return _short(s, limit)


def _short(text: str, limit: int = 110) -> str:
    """Trim to `limit` characters on a clean boundary, keeping the advice part."""
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(text) <= limit:
        return re.sub(r"\s-\s", " — ", text)
    parts = [p.strip() for p in re.split(r"\s[-–—]\s", text) if p.strip()]
    for k in (2, 1):
        if len(parts) >= k:
            cand = " — ".join(parts[-k:])
            if 30 <= len(cand) <= limit:
                return cand[0].upper() + cand[1:]
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(",;:- ")
    return cut + "…"


def _strip_name(text: str, name: str) -> str:
    first = (name or "").split()[0] if name else ""
    if first:
        text = re.sub(rf"^{re.escape(first)},\s*", "", text)
        text = text[:1].upper() + text[1:]
    return text


# ---- the votes ---------------------------------------------------------------

def _tone_vote(tone: Any) -> int:
    t = str(tone or "").lower()
    if t in ("auspicious", "good", "supportive", "up"):
        return 1
    if t in ("inauspicious", "caution", "challenging", "down", "stressed"):
        return -1
    return 0


def _votes(reading: dict) -> list[dict]:
    """Every signal that can speak for or against today, as {key,label,vote,text}."""
    out: list[dict] = []

    def add(key: str, label: str, vote: int, text: str) -> None:
        out.append({"key": key, "label": label, "vote": vote, "text": text})

    tara = reading.get("tarabala") or {}
    if tara:
        add("tara", "Star strength", _tone_vote(tara.get("tone")),
            str(tara.get("name") or ""))
    chandra = reading.get("chandrabal") or {}
    if chandra:
        add("chandra", "Moon strength", _tone_vote(chandra.get("tone")),
            str(chandra.get("name") or ""))

    gochar = reading.get("gochar") or {}
    for key, label in (("moon", "Moon's path"), ("sun", "Sun's path"),
                       ("mercury", "Mercury's path")):
        g = gochar.get(key)
        if isinstance(g, dict) and ("auspicious" in g or "inauspicious" in g):
            v = 1 if g.get("auspicious") else (-1 if g.get("inauspicious") else 0)
            add(key, label, v, "")

    av = reading.get("ashtakavarga") or {}
    moon = av.get("moon") or {}
    sav = moon.get("sav")
    if isinstance(sav, (int, float)):
        add("moon_sav", "Moon's sign strength",
            1 if sav >= 31 else (-1 if sav < 25 else 0), f"{int(sav)}")
    bav = moon.get("bav")
    if isinstance(bav, (int, float)):
        add("moon_bav", "Moon's house points",
            1 if bav >= 5 else (-1 if bav <= 2 else 0), f"{int(bav)}/8")
    sun_bav = (av.get("sun") or {}).get("bav")
    if isinstance(sun_bav, (int, float)):
        add("sun_bav", "Sun's house points",
            1 if sun_bav >= 5 else (-1 if sun_bav <= 2 else 0), f"{int(sun_bav)}/8")
    return out


def _vote(votes: list[dict], *keys: str) -> int:
    return sum(v["vote"] for v in votes if v["key"] in keys)


def _tone_from(score: int) -> str:
    return UP if score >= 1 else (DOWN if score <= -1 else MIXED)


def day_strength(votes: list[dict], base_tone: str = "") -> int:
    """1-10. Mean vote mapped onto the scale, nudged by the overall tone."""
    if not votes:
        return 5
    mean = sum(v["vote"] for v in votes) / len(votes)
    score = 5.5 + 3.5 * mean
    t = (base_tone or "").lower()
    if "caution" in t or "sensitive" in t:
        score -= 0.6
    elif t in ("bright", "positive"):
        score += 0.4
    return max(1, min(10, int(round(score))))


# ---- tiles -------------------------------------------------------------------

_ORD = {1: "1st", 2: "2nd", 3: "3rd"}
# The houses that speak to money, and which way they lean when the Moon crosses them.
_MONEY_HOUSES = {
    2: (1, "savings and security"),
    11: (1, "income and gains"),
    5: (0, "speculation and risk"),
    9: (0, "fortune and elders' help"),
    6: (-1, "debts and everyday costs"),
    8: (-1, "joint money and sudden change"),
    12: (-1, "expenses and letting go"),
}


def _money_line(reading: dict, chandra: dict) -> tuple[str, int]:
    """One money line from the signals that actually speak to money.

    The Moon's house from the rising sign decides whether today touches savings,
    gains or spending; failing that, Mercury (trade) today; failing that, the
    Sampat star, which is the wealth star in the Tara cycle. The Chandrabal
    do-note is a different thing (it is about mood by the Moon's sign), so it is
    never quoted as money advice.
    """
    h = _g(reading, "moon_transit", "house_from_lagna")
    if h in _MONEY_HOUSES:
        lean, theme = _MONEY_HOUSES[h]
        nth = _ORD.get(h, f"{h}th")
        if lean > 0:
            return f"The Moon crosses your {nth} house of {theme}: a good day to act on money matters.", 1
        if lean < 0:
            return f"The Moon crosses your {nth} house of {theme}: keep spending deliberate.", -1
        return f"The Moon crosses your {nth} house of {theme}; judge offers on their merits.", 0
    merc = re.sub(r"\s*\([^)]*\)", "", str(reading.get("mercury_narrative") or "")).strip()
    if merc:
        return _first_sentence(merc, 125), 0
    if "sampat" in str(chandra.get("name") or "").lower() and chandra.get("do_note"):
        return str(chandra["do_note"]), 1
    return "", 0

def _tiles(reading: dict, votes: list[dict]) -> list[dict]:
    vc = reading.get("vedic_confluence") or {}
    tiles: list[dict] = []

    work_votes = _vote(votes, "sun", "sun_bav")
    if _g(reading, "moon_transit", "house_from_lagna") == 10:
        work_votes += 1
    work = _first_sentence(vc.get("work_hint"))
    if work:
        tiles.append({"key": "work", "label": "Work", "tone": _tone_from(work_votes),
                      "text": work if work.lower().startswith(("in ", "at ", "for ")) else f"At work, {work}"})

    chandra = reading.get("chandrabal") or {}
    money, money_adj = _money_line(reading, chandra)
    if money:
        tiles.append({"key": "money", "label": "Money",
                      "tone": _tone_from(_vote(votes, "moon_sav", "mercury") + money_adj),
                      "text": _short(money, 130)})

    personal = str(vc.get("personal_hint") or "")
    rel = ""
    m = re.search(r"Relationships:\s*(.+?)(?:\s+Creativity and children:|$)", personal, re.S)
    if m:
        rel = _first_sentence(m.group(1))
    elif personal:
        rel = _first_sentence(personal)
    if rel:
        tiles.append({"key": "people", "label": "People & love",
                      "tone": _tone_from(_vote(votes, "tara", "moon")),
                      "text": rel if rel.lower().startswith(("in ", "with ")) else f"In relationships, {rel}"})

    mind = _first_sentence(_g(reading, "moonology", "sign_summary"), 125)
    if mind:
        tiles.append({"key": "mind", "label": "Mind & mood",
                      "tone": _tone_from(_vote(votes, "moon", "moon_bav")),
                      "text": mind})
    return tiles


# ---- do / don't ----------------------------------------------------------------

def _rank(item: dict) -> int:
    src = str(item.get("source") or "").lower()
    for i, key in enumerate(_SRC_ORDER):
        if key in src:
            return i
    return len(_SRC_ORDER)


_TARA = r"(?:Parama Mitra|Janma|Sampat|Vipat|Kshema|Pratyak|Sadhana|Naidhana|Mitra|Ati Mitra)"


def _plain_terms(text: str) -> str:
    """Swap the jargon that shows up in engine Do/Don't lines for plain words."""
    text = re.sub(rf"^{_TARA}(?= is\b)", "Your star", text)
    text = re.sub(r"\bPratyantar (\w+)", r"the \1 sub-period", text)
    return text[:1].upper() + text[1:]


def _lines(items: Any, name: str, n: int) -> list[str]:
    rows = [it for it in (items or []) if isinstance(it, dict) and it.get("text")]
    rows = [it for it in rows
            if not any(k in str(it.get("source") or "") for k in _REDUNDANT_SRC)]
    rows.sort(key=_rank)
    out: list[str] = []
    for it in rows:
        line = _plain_terms(_short(_strip_name(str(it["text"]), name), 105))
        if line and line not in out:
            out.append(line)
        if len(out) >= n:
            break
    return out


# ---- timing --------------------------------------------------------------------

_BEST = ("Amrit", "Labh", "Shubha", "Chara")


def _hm(t: Any) -> str:
    return str(t or "")[:5]


def timing(reading: dict) -> dict:
    """{best:[{label,when,plain}], avoid:[...]} — short and ready to print."""
    w = _g(reading, "muhurat", "windows", default={}) or {}
    best: list[dict] = []
    good = sorted((x for x in (w.get("good_choghadiya") or []) if isinstance(x, dict)),
                  key=lambda x: _BEST.index(x.get("label")) if x.get("label") in _BEST else 9)
    for x in good[:2]:
        best.append({"label": str(x.get("label")), "when": f"{_hm(x.get('start'))}–{_hm(x.get('end'))}",
                     "plain": re.sub(r"\s-\s", " — ", str(x.get("plain") or ""))})
    ab = w.get("abhijit")
    if isinstance(ab, dict) and ab.get("start"):
        best.append({"label": "Abhijit", "when": f"{_hm(ab.get('start'))}–{_hm(ab.get('end'))}",
                     "plain": "Midday safety-net window when the rest of the day is mixed."})
    best.sort(key=lambda r: r["when"])
    avoid: list[dict] = []
    for x in (w.get("tri_kaal") or []):
        if isinstance(x, dict) and x.get("label") == "Rahu Kaal":
            avoid.append({"label": "Rahu Kaal", "when": f"{_hm(x.get('start'))}–{_hm(x.get('end'))}",
                          "plain": "Skip new starts, signatures and ceremonies."})
    dm = w.get("durmuhurta") or []
    if dm and isinstance(dm[0], dict):
        avoid.append({"label": "Durmuhurta", "when": f"{_hm(dm[0].get('start'))}–{_hm(dm[0].get('end'))}",
                      "plain": "A poor slot for starting anything important."})
    return {"best": best, "avoid": avoid}


# ---- the summary -----------------------------------------------------------------

_STAR_PLAIN = {
    1: "Your star strength is high today",
    0: "Your star strength is middling today",
    -1: "Your star strength is low today",
}
_JOIN = {  # (star vote, moon vote) -> connective + Moon clause
    (1, 1): "and the Moon backs you",
    (1, 0): "and the Moon is neutral",
    (1, -1): "but the Moon asks for care",
    (0, 1): "though the Moon backs you",
    (0, 0): "and the Moon is neutral",
    (0, -1): "and the Moon asks for care",
    (-1, 1): "though the Moon backs you",
    (-1, 0): "so pace yourself",
    (-1, -1): "and the Moon asks for care too, so pace yourself",
}


def _headline(reading: dict) -> tuple[str, str]:
    """(headline, advice) from the confluence verdict: 'A workable day - move ...'."""
    vc = reading.get("vedic_confluence") or {}
    plain = str(vc.get("verdict_plain") or "").strip()
    plain = re.sub(r"^Overall:\s*", "", plain, flags=re.I)
    if not plain:
        return "A steady day.", "Move with your own timing."
    parts = re.split(r"\s[-–—]\s", plain, maxsplit=1)
    head = parts[0].strip().rstrip(".")
    tail = parts[1].strip().rstrip(".") if len(parts) > 1 else ""
    return (head[0].upper() + head[1:] + ".",
            (tail[0].upper() + tail[1:] + ".") if tail else "")


def _focus(reading: dict) -> str:
    house = _g(reading, "moon_transit", "house_from_moon")
    theme = HOUSE_LIFE_THEME.get(house, "") if isinstance(house, int) else ""
    if not theme:
        return ""
    return ", ".join([p.strip() for p in theme.split(",")][:3]).replace(" and ", ", ")


def build(reading: dict, name: str = "") -> dict:
    votes = _votes(reading)
    total = len(votes)
    pos = sum(1 for v in votes if v["vote"] > 0)
    neg = sum(1 for v in votes if v["vote"] < 0)
    score = day_strength(votes, str(reading.get("tone") or ""))
    tone = UP if score >= 7 else (DOWN if score <= 4 else MIXED)

    lean = "good" if pos >= neg else "careful"
    agree = max(pos, neg) if (pos or neg) else 0

    tara_v = _vote(votes, "tara")
    moon_v = _vote(votes, "chandra")
    theme_line = ""
    opening = str(reading.get("opening") or "")
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", opening) if s.strip()]
    for s in sentences:
        if s.lower().startswith("the moon in"):
            theme_line = s
            break
    bits = [theme_line] if theme_line else []
    if votes:
        bits.append(f"{_STAR_PLAIN[tara_v]}, {_JOIN[(tara_v, moon_v)]}.")
    head, advice = _headline(reading)
    if advice:
        bits.insert(0, advice)
    summary = " ".join(bits)

    donts = _lines(reading.get("donts"), name, 3)
    return {
        "headline": head,
        "summary": summary,
        "score": score,
        "tone": tone,
        "tone_word": {UP: "Leaning good", MIXED: "Steady", DOWN: "Go gently"}[tone],
        "checks": {"agree": agree, "total": total, "lean": lean},
        "votes": votes,
        "tiles": _tiles(reading, votes),
        "focus": _focus(reading),
        "watch": donts[0] if donts else "",
        "dos": _lines(reading.get("dos"), name, 3),
        "donts": donts,
        "timing": timing(reading),
    }
