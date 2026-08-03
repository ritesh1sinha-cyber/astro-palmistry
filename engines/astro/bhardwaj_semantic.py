#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bhardwaj_semantic.py  MiniLM semantic confluence for Bhardwaj book predictions.

Maps THIS chart's facts to Bhardwaj OCR/book corpus via all-MiniLM-L6-v2 (local models/).
Direct planet-in-house / lord-in-house lookup first; semantic match as supplement only.
Outputs affirmative, second-person prose  not generic if/else templates.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "models" / "all-MiniLM-L6-v2"
DATA_PATH = BASE_DIR / "bhardwaj_book_data.json"

DOMAINS = (
    "personality", "career", "finance", "marriage", "children",
    "health", "property", "travel", "spiritual", "current",
)
DOMAIN_TITLE = {
    "personality": "Who You Are",
    "career": "Career & Public Life",
    "finance": "Wealth & Resources",
    "marriage": "Partnership & Home Rhythm",
    "children": "Children & Creativity",
    "health": "Health & Resilience",
    "property": "Home & Property",
    "travel": "Travel & Fortune",
    "spiritual": "Inner Life & Dharma",
    "current": "Where You Stand Now",
}
HOUSE_DOMAIN = {
    1: "personality", 2: "finance", 3: "personality", 4: "property",
    5: "children", 6: "health", 7: "marriage", 8: "health", 9: "travel",
    10: "career", 11: "finance", 12: "spiritual",
}
STRONG = {"exalted", "own_sign", "moolatrikona", "great_friend_sign"}
WEAK = {"debilitated", "enemy_sign"}
CONF_LABEL = [(5, "HIGH"), (3, "MODERATE"), (2, "LOW"), (1, "SPECULATIVE")]

CAUTION_START = re.compile(
    r"^(If |In case of|When |With weak|If the |If a weak|If there is a weak|If afflicted|If moon is waning)",
    re.I,
)

THEME_ANCHORS: dict[str, list[str]] = {
    "personality": [
        "ascendant lagna character temperament intellect communication gemini mercury mind",
        "birth sign moon emotional nature appearance height complexion",
    ],
    "career": [
        "tenth house profession job government business success fame authority dashamsha",
        "public standing promotion leadership state official recognition",
    ],
    "finance": [
        "second house wealth money family speech savings dhan bhava income gains",
        "eleventh house labha gains income prosperity bank balance",
    ],
    "marriage": [
        "seventh house spouse marriage partnership wife husband manglik sexual",
        "domestic harmony relationship delay marriage ascendant",
    ],
    "children": [
        "fifth house children progeny son daughter education creativity putr bhava",
        "pregnancy intellectual offspring speculation",
    ],
    "health": [
        "sixth house disease enemy illness accident rheumatism stomach pain",
        "eighth house longevity hidden suffering maraka transformation",
    ],
    "property": [
        "fourth house mother home vehicle land house property sukha",
        "real estate domestic comfort agriculture",
    ],
    "travel": [
        "ninth house fortune dharma father pilgrimage foreign bhagya luck",
        "travel abroad migration long journey religion",
    ],
    "spiritual": [
        "twelfth house moksha expenses foreign ketu detachment meditation charity",
        "mantra yantra spiritual worship remedy",
    ],
    "current": [
        "vimshottari dasha mahadasha antardasha current period timing now",
        "gochar transit today planetary movement chandra lagna",
    ],
}


@dataclass
class BookChunk:
    text: str
    kind: str
    domain: str
    tags: str = ""


@dataclass
class Signal:
    source: str
    domain: str
    direction: str
    timing: str
    text: str
    anchor: str = ""
    planet: str = ""
    house: int = 0
    lord_of: int = 0
    lord_in: int = 0
    dignity: str = ""


@dataclass
class Cluster:
    domain: str
    direction: str
    timing: str
    sources: list[str] = field(default_factory=list)
    affirmation: str = ""
    confidence: str = "SPECULATIVE"
    score: float = 0.0
    book_refs: list[str] = field(default_factory=list)


def _clean_ocr(text: str) -> str:
    text = re.sub(r"========== PAGE \d+ ==========.*?ASTROLOGY\s*", " ", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _sentences(text: str, min_len: int = 40) -> list[str]:
    text = _clean_ocr(text)
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) >= min_len]


def _personalize(text: str) -> str:
    t = text.strip()
    pairs = [
        (r"\bthe native\b", "you"),
        (r"\bThe native has\b", "You have"),
        (r"\bthe native has\b", "you have"),
        (r"\bThe native\b", "You"),
        (r"\ba native\b", "you"),
        (r"\bA native\b", "You"),
        (r"\bhe/she\b", "you"),
        (r"\bHe/she\b", "You"),
        (r"\bhe will\b", "you will"),
        (r"\bHe will\b", "You will"),
        (r"\bhe is\b", "you are"),
        (r"\bHe is\b", "You are"),
        (r"\byou is\b", "you are"),
        (r"\bYou is\b", "You are"),
        (r"\bhis\b", "your"),
        (r"\bHis\b", "Your"),
        (r"\bhim\b", "you"),
        (r"\bHim\b", "You"),
        (r"\bThe person is\b", "You are"),
        (r"\bthe person is\b", "you are"),
        (r"\bThe person will\b", "You will"),
        (r"\bthe person will\b", "you will"),
        (r"\bthe person\b", "you"),
        (r"\bThe person\b", "You"),
    ]
    for pat, rep in pairs:
        t = re.sub(pat, rep, t)
    t = re.sub(r"^If (?:the )?(?:\w+ )?(?:is )?(?:weak|strong|placed)[^.]*\.\s*", "", t, flags=re.I)
    t = re.sub(r"\s+If afflicted[^.]*\.", ".", t, flags=re.I)
    t = re.sub(r"If afflicted[^.]*\.\s*", "", t, flags=re.I)
    t = re.sub(r"In case of weak[^.]*\.\s*", "", t, flags=re.I)
    t = re.sub(r"When weak[^.]*\.\s*", "", t, flags=re.I)
    t = re.sub(r"\bYou is\b", "You are", t)
    t = re.sub(r"\byou is\b", "you are", t)
    t = re.sub(r"\bYou gets\b", "You get", t)
    t = re.sub(r"\byou gets\b", "you get", t)
    t = re.sub(r"\byou has\b", "you have", t)
    t = re.sub(r"\bhimself on your own\b", "yourself on your own", t)
    if t and t[0].islower():
        t = t[0].upper() + t[1:]
    return t


def _is_conditional(s: str) -> bool:
    return bool(CAUTION_START.match(s.strip()))


def _sentence_polarity(s: str) -> str:
    if _is_conditional(s):
        return "caution"
    low = s.lower()
    if re.search(r"\b(free from enemies|defeating (?:his )?opponents|destroyer of enemies)\b", low):
        return "positive"
    if re.search(
        r"\b(suffer|devoid of|unhappy|luckless|cheat|restless|humiliated|sick|obstruct|"
        r"pain|disease|unfortunate|loss of|without happiness|grab the wealth|unfair means)\b",
        low,
    ):
        return "caution"
    return "positive"


def pick_book_clause(raw: str, dignity: str = "", direction: str = "neutral") -> str:
    """Pick the best Bhardwaj sentence for this placement  affirmative, not if/else."""
    if not raw or not raw.strip():
        return ""
    raw = re.split(
        r"Ekadshesh Position|Position In Various Houses|\s-------+\s",
        _clean_ocr(raw),
        maxsplit=1,
        flags=re.I,
    )[0]
    sents = _sentences(raw, min_len=22)
    if not sents:
        return _personalize(raw[:320])

    plain = [s for s in sents if _sentence_polarity(s) == "positive" and not _is_conditional(s)]
    caution = [s for s in sents if _sentence_polarity(s) == "caution" or _is_conditional(s)]

    want_positive = direction == "positive" or dignity in STRONG
    want_caution = direction == "caution" and dignity in WEAK

    if want_positive or not want_caution:
        pool = plain or [s for s in sents if not _is_conditional(s)] or sents
        line = _personalize(pool[0])
        if dignity in WEAK and direction != "positive":
            dig = dignity.replace("_", " ")
            line += f" Your chart shows {dig} strength here — steady discipline brings this out fully."
        return line

    if plain:
        return _personalize(plain[0])
    if caution:
        c = _personalize(caution[0])
        if not c.lower().startswith("you"):
            c = "You carry a mixed pattern here: " + c[0].lower() + c[1:]
        return c
    return _personalize(sents[0])


def lookup_planet_house(book: dict, planet: str, house: int, dignity: str, direction: str) -> str:
    raw = book.get("planet_in_house", {}).get(str(house), {}).get(planet, "")
    return pick_book_clause(raw, dignity, direction)


def lookup_house_lord(book: dict, lord_of: int, lord_in: int, direction: str) -> str:
    raw = book.get("house_lord_in_house", {}).get(str(lord_of), {}).get(str(lord_in), "")
    return pick_book_clause(raw, "", direction)


def lookup_lagna_sign(book: dict, sign: str, direction: str = "positive") -> str:
    raw = book.get("lagna_signs", {}).get(sign, "")
    return pick_book_clause(raw, "", direction)


def _tag_overlap(chunk: BookChunk, hint: str) -> float:
    if not hint or not chunk.tags:
        return 0.0
    h = hint.lower().split()
    t = chunk.tags.lower()
    if all(tok in t for tok in h):
        return 0.55
    if h and h[0] in t:
        return 0.18
    return 0.0


def _chunk_ok(text: str, tag_hint: str = "") -> bool:
    if len(text) > 380:
        return False
    if "Position In Various Houses" in text or "-------" in text:
        return False
    if text.count("In the ") >= 3:
        return False
    if re.search(r"\b(Moon|Mars|Sun|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu)\s*-\s*", text):
        return False
    if tag_hint:
        m = re.match(r"(\w+)\s+h(\d+)", tag_hint)
        if m:
            pl, h = m.group(1), m.group(2)
            wrong = re.findall(rf"In the (\w+) house", text, re.I)
            for wh in wrong:
                if wh.lower() not in ("first", "second", "third", "fourth", "fifth", "sixth",
                                      "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth"):
                    continue
                ord_map = {"first": "1", "second": "2", "third": "3", "fourth": "4", "fifth": "5",
                           "sixth": "6", "seventh": "7", "eighth": "8", "ninth": "9", "tenth": "10",
                           "eleventh": "11", "twelfth": "12"}
                if ord_map.get(wh.lower(), "") != h:
                    return False
            if pl.lower() not in text.lower()[:40] and chunk_kind_planet_mismatch(text, pl):
                pass
    return True


def chunk_kind_planet_mismatch(text: str, planet: str) -> bool:
    others = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
    for o in others:
        if o != planet and re.match(rf"^{o}\s", text, re.I):
            return True
    return False


def _conf_label(n: float) -> str:
    for thresh, label in CONF_LABEL:
        if n >= thresh:
            return label
    return "SPECULATIVE"


def _ord(n: int) -> str:
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n if n < 20 else n % 10, 'th')}"


def load_corpus(book: dict) -> list[BookChunk]:
    chunks: list[BookChunk] = []
    for sign, body in book.get("lagna_signs", {}).items():
        clause = pick_book_clause(body, "", "positive")
        if clause and _chunk_ok(clause):
            chunks.append(BookChunk(clause, "lagna_sign", "personality", sign))

    for h, pls in book.get("planet_in_house", {}).items():
        dom = HOUSE_DOMAIN.get(int(h), "personality")
        for pl, body in pls.items():
            clause = pick_book_clause(body, "", "positive")
            if clause and _chunk_ok(clause, f"{pl} h{h}"):
                chunks.append(BookChunk(clause, "planet_in_house", dom, f"{pl} h{h}"))

    for lh, occs in book.get("house_lord_in_house", {}).items():
        for oh, body in occs.items():
            dom = HOUSE_DOMAIN.get(int(oh), "personality")
            clause = pick_book_clause(body, "", "neutral")
            if clause and _chunk_ok(clause):
                chunks.append(BookChunk(clause, "house_lord", dom, f"lord{lh} in h{oh}"))

    for p in book.get("dasha_principles", []):
        chunks.append(BookChunk(p, "dasha_rule", "current", "vimshottari"))

    seen: set[str] = set()
    out: list[BookChunk] = []
    for c in chunks:
        key = c.text[:90].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


class BhardwajSemanticEngine:
    def __init__(self, book: Optional[dict] = None):
        from local_models import load_sentence_transformer

        self.model = load_sentence_transformer()
        self.book = book or json.loads(DATA_PATH.read_text(encoding="utf-8"))
        self.chunks = load_corpus(self.book)
        self._chunk_emb = self.model.encode(
            [c.text for c in self.chunks], normalize_embeddings=True, show_progress_bar=False,
        )
        self._anchor_emb: dict[str, np.ndarray] = {}
        for dom, anchors in THEME_ANCHORS.items():
            self._anchor_emb[dom] = self.model.encode(anchors, normalize_embeddings=True)

    def assign_domain(self, text: str) -> str:
        emb = self.model.encode([text], normalize_embeddings=True)[0]
        best, sc = "personality", -1.0
        for dom, amat in self._anchor_emb.items():
            s = float(np.max(amat @ emb))
            if s > sc:
                sc, best = s, dom
        return best

    def match_book(
        self,
        query: str,
        domain: Optional[str] = None,
        k: int = 2,
        tag_hint: str = "",
        direction: str = "neutral",
    ) -> list[tuple[BookChunk, float]]:
        emb = self.model.encode([query], normalize_embeddings=True)[0]
        scores: list[tuple[int, float]] = []
        for i, c in enumerate(self.chunks):
            if domain and c.domain != domain:
                continue
            if direction == "positive" and _is_conditional(c.text):
                continue
            if tag_hint and _tag_overlap(c, tag_hint) < 0.1:
                if c.kind == "planet_in_house":
                    continue
            sc = float(self._chunk_emb[i] @ emb) + _tag_overlap(c, tag_hint)
            scores.append((i, sc))
        scores.sort(key=lambda x: -x[1])
        out: list[tuple[BookChunk, float]] = []
        for i, sc in scores[: k * 4]:
            if sc < 0.32:
                break
            out.append((self.chunks[i], sc))
            if len(out) >= k:
                break
        return out

    def affirm_from_chart(
        self,
        members: list[Signal],
        domain: str,
        direction: str,
    ) -> tuple[str, list[str]]:
        """Build affirmation from direct book lookup on chart signals."""
        book_lines: list[str] = []
        refs: list[str] = []

        def dignity_rank(d: str) -> int:
            if d in STRONG:
                return 3
            if d in WEAK:
                return 0
            return 1

        ranked = sorted(
            members,
            key=lambda m: (dignity_rank(m.dignity), -m.house if m.house else 0),
            reverse=True,
        )
        max_lines = 2 if direction == "positive" else 1

        for m in ranked:
            if len(book_lines) >= max_lines:
                break
            line_dir = direction
            if m.direction == "positive" and direction != "caution":
                line_dir = "positive"
            elif m.direction == "caution":
                line_dir = "caution"

            if m.planet and m.house:
                line = lookup_planet_house(self.book, m.planet, m.house, m.dignity, line_dir)
                if line and line not in book_lines:
                    if book_lines and direction == "positive" and _sentence_polarity(line) == "caution":
                        continue
                    book_lines.append(line)
                    refs.append(f"planet_in_house: {m.planet} h{m.house}")
            elif m.lord_of and m.lord_in:
                line = lookup_house_lord(self.book, m.lord_of, m.lord_in, line_dir)
                if line and line not in book_lines:
                    book_lines.append(line)
                    refs.append(f"house_lord: lord{m.lord_of} in h{m.lord_in}")
            elif m.source == "Lagna chapter":
                lagna = re.search(r"(\w+) ascendant", m.text)
                if lagna:
                    line = lookup_lagna_sign(self.book, lagna.group(1), "positive")
                    if line and line not in book_lines:
                        book_lines.append(line)
                        refs.append(f"lagna: {lagna.group(1)}")
            elif m.source == "Moon sign":
                moon = re.search(r"Moon birth sign (\w+)", m.text)
                if moon:
                    line = lookup_lagna_sign(self.book, moon.group(1), "positive")
                    if line and line not in book_lines:
                        book_lines.append(line)
                        refs.append(f"moon_sign: {moon.group(1)}")

        anchor = members[0].anchor or members[0].text[:160]
        if not anchor.endswith((".", "!", "?")):
            anchor = anchor.rstrip(".") + "."

        if book_lines:
            body = " ".join(book_lines[:2])
            return f"{anchor} {body}", refs

        tag_hint = ""
        for m in members:
            if m.planet and m.house:
                tag_hint = f"{m.planet} h{m.house}"
                break
        query = " ".join(m.text for m in members[:3])
        hits = self.match_book(query, domain=domain, k=1, tag_hint=tag_hint, direction=direction)
        if hits:
            line = _personalize(hits[0][0].text)
            refs.append(f"{hits[0][0].kind}: {hits[0][0].tags}")
            return f"{anchor} {line}", refs
        return anchor, refs

    def affirm(
        self,
        anchor: str,
        query: str,
        domain: Optional[str] = None,
        tag_hint: str = "",
        direction: str = "neutral",
    ) -> tuple[str, list[str]]:
        if tag_hint:
            m = re.match(r"(\w+)\s+h(\d+)", tag_hint)
            if m:
                line = lookup_planet_house(
                    self.book, m.group(1), int(m.group(2)), "", direction,
                )
                if line:
                    if not anchor.endswith((".", "!", "?")):
                        anchor = anchor.rstrip(".") + "."
                    return f"{anchor} {line}", [f"planet_in_house: {tag_hint}"]

        hits = self.match_book(query, domain=domain, k=1, tag_hint=tag_hint, direction=direction)
        if not hits:
            return anchor, []
        line = _personalize(hits[0][0].text)
        if not anchor.endswith((".", "!", "?")):
            anchor = anchor.rstrip(".") + "."
        return f"{anchor} {line}", [f"{hits[0][0].kind}: {hits[0][0].tags}"]

    def cluster(self, signals: list[Signal]) -> list[Cluster]:
        if not signals:
            return []
        for s in signals:
            if s.domain == "unknown":
                s.domain = self.assign_domain(s.text)

        embs = self.model.encode([s.text for s in signals], normalize_embeddings=True)
        clusters: list[Cluster] = []

        for dom in DOMAINS:
            idxs = [i for i, s in enumerate(signals) if s.domain == dom]
            if not idxs:
                continue
            members = [signals[i] for i in idxs]
            pos = sum(1 for m in members if m.direction == "positive")
            cau = sum(1 for m in members if m.direction == "caution")
            direction = "positive" if pos > cau else ("caution" if cau > pos else "neutral")
            timings = [m.timing for m in members if m.timing]
            timing = max(timings, key=len) if timings else ""

            affirmation, refs = self.affirm_from_chart(members, dom, direction)
            if timing and timing not in affirmation:
                affirmation += f" Active window in your dasha table: {timing}."

            sources = sorted({m.source for m in members})
            score = float(len(members))
            if len(idxs) > 1:
                sims = [float(embs[i] @ embs[j]) for a, i in enumerate(idxs) for j in idxs[a + 1:]]
                if sims and np.mean(sims) > 0.45:
                    score += 1.5
            clusters.append(Cluster(
                dom, direction, timing, sources, affirmation,
                _conf_label(score), score, refs,
            ))

        clusters.sort(key=lambda c: (-c.score, c.domain))
        return clusters


def _dignity_word(d: str) -> str:
    return d.replace("_", " ")


def _timing_window(ad: dict) -> str:
    if not ad:
        return ""
    try:
        from datetime import datetime
        s = datetime.strptime(ad["start"][:10], "%Y-%m-%d").date().strftime("%b %Y")
        e = datetime.strptime(ad["end"][:10], "%Y-%m-%d").date().strftime("%b %Y")
        return f"{s} - {e}"
    except ValueError:
        return ""


def build_chart_signals(chart, pc: dict) -> list[Signal]:
    """Chart-specific facts only  fed to semantic matcher."""
    s: list[Signal] = []
    lagna = chart.lagna
    moon = chart.moon_sign
    ll = chart.houses[1]["lord"]

    lagna_body = chart.book.get("lagna_signs", {}).get(lagna, "")
    s.append(Signal(
        "Lagna chapter", "personality", "neutral", "",
        f"{lagna} ascendant chart with Moon in {moon} ({chart.moon_nak} nakshatra). {lagna_body[:220]}",
        anchor=f"Your life opens through {lagna} rising  {ll} steers the body and first impression in this map.",
    ))
    if moon != lagna:
        moon_body = chart.book.get("lagna_signs", {}).get(moon, "")[:180]
        s.append(Signal(
            "Moon sign", "personality", "neutral", "",
            f"Moon birth sign {moon} colours emotion and habit. {moon_body}",
            anchor=f"Emotional rhythm runs through {moon}; it can equal or override lagna when stronger at birth.",
        ))

    house_dom = {5: "children", 7: "marriage", 10: "career", 11: "finance", 6: "health", 9: "travel", 4: "property"}
    pih = chart.book.get("planet_in_house", {})

    for pl, info in chart.planets.items():
        h = info["house"]
        dom = house_dom.get(h, HOUSE_DOMAIN.get(h, "personality"))
        dig = info["dignity"]
        ruled = chart.rules.get(pl, [])
        direction = "positive" if dig in STRONG or h in (1, 4, 5, 9, 10, 11) else (
            "caution" if dig in WEAK or h in (6, 8, 12) else "neutral"
        )
        if pl in ("Ketu", "Rahu", "Saturn") and h in (5, 7, 8) and dig not in STRONG:
            direction = "caution"
        ruled_txt = ", ".join(_ord(x) for x in ruled) if ruled else "no house lordship"
        anchor = (
            f"Your {pl} sits in the {_ord(h)} house ({info['sign']}, {_dignity_word(dig)}) "
            f"and rules {ruled_txt}."
        )
        s.append(Signal(
            f"{pl} in house", dom, direction, "",
            f"{anchor} Bhardwaj {pl} {_ord(h)} house {info['sign']} {_dignity_word(dig)}.",
            anchor=anchor,
            planet=pl, house=h, dignity=dig,
        ))

    for h in range(1, 13):
        lord = chart.houses[h]["lord"]
        occ = chart.planets[lord]["house"]
        dom = HOUSE_DOMAIN.get(h, "personality")
        book = chart.book.get("house_lord_in_house", {}).get(str(h), {}).get(str(occ), "")
        if not book:
            continue
        anchor = f"As lord of the {_ord(h)} house, {lord} sits in your {_ord(occ)} house."
        pol = _sentence_polarity(book)
        if h == 8 and occ == 6:
            direction = "positive"
        elif occ in (6, 8, 12) or pol == "caution":
            direction = "caution"
        elif occ in (1, 4, 5, 9, 10, 11) and pol != "caution":
            direction = "positive"
        else:
            direction = "neutral"
        s.append(Signal(
            f"Lord {h}", dom, direction, "",
            f"{anchor} Bhardwaj lord {lord} house {h} in {_ord(occ)}.",
            anchor=anchor,
            lord_of=h, lord_in=occ,
        ))

    # Marriage lane: 7th lord even when lord-in-house OCR is incomplete
    lord7 = chart.houses[7]["lord"]
    if lord7:
        occ7 = chart.planets[lord7]["house"]
        info7 = chart.planets[lord7]
        if not any(x.source == "Lord 7" for x in s):
            s.append(Signal(
                "Marriage lord", "marriage", "neutral", "",
                f"7th lord {lord7} in {_ord(occ7)}.",
                anchor=(
                    f"Marriage and partnership run through {lord7}, placed in your "
                    f"{_ord(occ7)} house ({info7['sign']}, {_dignity_word(info7['dignity'])})."
                ),
                planet=lord7, house=occ7, dignity=info7["dignity"],
            ))

    for y in chart.detect_yogas():
        s.append(Signal(
            "Yoga", "personality", "positive", "",
            f"Yoga {y['name']}: {y['result']}",
            anchor=f"Your chart forms {y['name']}  a fixed signature in Bhardwaj's auspicious combinations chapter.",
        ))

    vim = pc.get("vimshottari", {})
    md = vim.get("current_md", {}).get("md_lord", "")
    cur_ad = next((a for a in vim.get("current_md_antardashas", []) if a.get("status") == "current"), None)
    ad_lord = cur_ad.get("ad_lord", "") if cur_ad else ""
    rng = _timing_window(cur_ad) if cur_ad else ""
    if md:
        md_info = chart.planets.get(md, {})
        mh = md_info.get("house", 0)
        md_dig = md_info.get("dignity", "")
        anchor = (
            f"You are inside {md} mahadasha with {ad_lord} antardasha ({rng})  "
            f"the chapter ruler sits in your {_ord(mh)} house."
        )
        s.append(Signal(
            "Vimshottari", "current", "neutral", rng,
            f"{anchor} Bhardwaj vimshottari dasha {md} house {mh}.",
            anchor=anchor,
            planet=md, house=mh, dignity=md_dig,
        ))
        if ad_lord and ad_lord != md:
            ah = chart.planets[ad_lord]["house"]
            ad_dig = chart.planets[ad_lord]["dignity"]
            ad_dom = house_dom.get(ah, "current")
            s.append(Signal(
                "Antardasha", ad_dom, "neutral", rng,
                f"Sub-period lord {ad_lord} in {_ord(ah)} house activates now.",
                anchor=(
                    f"The running antardasha lord {ad_lord} pulls "
                    f"{DOMAIN_TITLE.get(ad_dom, ad_dom).lower()} forward through the {_ord(ah)} house."
                ),
                planet=ad_lord, house=ah, dignity=ad_dig,
            ))

    return s
