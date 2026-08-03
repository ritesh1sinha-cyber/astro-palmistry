#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Jaimini structure chart for book-section lane (no Chara dasha timing)."""
from __future__ import annotations

from dataclasses import dataclass, field

from astro_precompute import d9_sign

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]
SIGN_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}
MOVABLE = {"Aries", "Cancer", "Libra", "Capricorn"}
FIXED = {"Taurus", "Leo", "Scorpio", "Aquarius"}
DUAL = {"Gemini", "Virgo", "Sagittarius", "Pisces"}
NAT_BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}
NAT_MALEFIC = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
ROLE_ORDER = [
    "Atmakarak", "Amatyakarak", "Bhratrukaraka", "Matrukaraka",
    "Putrakaraka", "Gnatikaraka", "Darakaraka",
]
ROLE_SHORT = {
    "Atmakarak": "AK", "Amatyakarak": "AmK", "Bhratrukaraka": "BK",
    "Matrukaraka": "MK", "Putrakaraka": "PK", "Gnatikaraka": "GK", "Darakaraka": "DK",
}


def house_of(sign: str, lagna: str) -> int:
    return (SIGNS.index(sign) - SIGNS.index(lagna)) % 12 + 1


def sign_at(lagna: str, offset: int) -> str:
    return SIGNS[(SIGNS.index(lagna) + offset - 1) % 12]


def sign_category(sign: str) -> str:
    if sign in MOVABLE:
        return "movable"
    if sign in FIXED:
        return "fixed"
    return "dual"


def sign_aspects_from(sign: str) -> set[str]:
    idx = SIGNS.index(sign)
    cat = sign_category(sign)
    if cat == "movable":
        adj = SIGNS[(idx + 1) % 12]
        return {s for s in FIXED if s != adj}
    if cat == "fixed":
        adj = SIGNS[(idx - 1) % 12]
        return {s for s in MOVABLE if s != adj}
    return {s for s in DUAL if s != sign}


def mutual_sign_aspect(a: str, b: str) -> bool:
    return b in sign_aspects_from(a) and a in sign_aspects_from(b)


def navamsa_sign(sign: str, deg_in_sign: float) -> str:
    lon = SIGNS.index(sign) * 30.0 + float(deg_in_sign)
    return SIGNS[int(lon / (30.0 / 9.0)) % 12]


def arudha_pada(bhava_sign: str, lord_sign: str) -> str:
    n = (SIGNS.index(lord_sign) - SIGNS.index(bhava_sign)) % 12 + 1
    pada_idx = (SIGNS.index(lord_sign) + n - 1) % 12
    pada = SIGNS[pada_idx]
    rel = (SIGNS.index(pada) - SIGNS.index(bhava_sign)) % 12 + 1
    if rel in (1, 7):
        pada = SIGNS[(pada_idx + 9) % 12]
    return pada


def _ord(n: int) -> str:
    return "%d%s" % (n, {1: "st", 2: "nd", 3: "rd"}.get(n if n < 20 else n % 10, "th"))


@dataclass
class JaiminiBooksChart:
    pc: dict
    name: str
    lagna: str
    karakamsa: str | None
    karakas: dict = field(default_factory=dict)
    arudha_lagna: str = ""
    upapada: str = ""
    fifth_lord: str = ""
    _by_sign: dict = field(default_factory=dict)

    @classmethod
    def from_precompute(cls, pc: dict) -> "JaiminiBooksChart":
        lagna = pc["meta"]["lagna_sign"]
        karakas = {}
        for k in pc.get("cara_karakas", {}).get("karakas", []):
            sign = k.get("sign")
            karakas[k["role"]] = {
                "planet": k["planet"],
                "sign": sign,
                "house": house_of(sign, lagna) if sign in SIGNS else k.get("house"),
                "dignity": k.get("dignity", ""),
            }
        ak = karakas.get("Atmakarak", {})
        akp = ak.get("planet")
        jm = pc.get("jaimini", {})
        kl = jm.get("karakamsa_sign") or (d9_sign(pc, akp) if akp else None)
        by_sign: dict[str, list[str]] = {}
        for nm, v in pc["planets"].items():
            by_sign.setdefault(v["sign"], []).append(nm)
        h12 = sign_at(lagna, 12)
        al = arudha_pada(lagna, pc["planets"][SIGN_LORD[lagna]]["sign"])
        up = arudha_pada(h12, pc["planets"][SIGN_LORD[h12]]["sign"])
        fifth_sign = sign_at(lagna, 5)
        fifth_lord = SIGN_LORD[fifth_sign]
        return cls(
            pc=pc,
            name=pc["meta"]["client"],
            lagna=lagna,
            karakamsa=kl,
            karakas=karakas,
            arudha_lagna=al,
            upapada=up,
            fifth_lord=fifth_lord,
            _by_sign=by_sign,
        )

    def role(self, r: str) -> dict:
        return self.karakas.get(r, {})

    def planets_in(self, sign: str) -> list[str]:
        return list(self._by_sign.get(sign, []))

    def planet_house(self, planet: str) -> int:
        pl = self.pc["planets"].get(planet)
        return house_of(pl["sign"], self.lagna) if pl else 0

    def kl_house(self, sign: str) -> int:
        if not self.karakamsa or sign not in SIGNS:
            return 0
        return house_of(sign, self.karakamsa)

    def planets_in_kl_house(self, h: int) -> list[str]:
        if not self.karakamsa:
            return []
        target = sign_at(self.karakamsa, h)
        return self.planets_in(target)

    def argala_on(self, ref_sign: str) -> dict:
        """Principal argala 2/4/11 vs obstruction 12/10/3 from ref_sign."""
        fav, blocked, open_h = [], [], []
        for ah, vh in zip((4, 2, 11), (10, 12, 3)):
            a_sign, v_sign = sign_at(ref_sign, ah), sign_at(ref_sign, vh)
            a_pl, v_pl = self.planets_in(a_sign), self.planets_in(v_sign)
            if a_pl and not v_pl:
                open_h.append(ah)
                fav.append(f"{', '.join(a_pl)} from {_ord(ah)} ({a_sign})")
            elif a_pl and v_pl:
                blocked.append(f"{', '.join(a_pl)} in {a_sign} blocked by {', '.join(v_pl)} in {v_sign}")
        vip = self.planets_in(sign_at(ref_sign, 3))
        vip_count = sum(1 for p in vip if p in NAT_MALEFIC)
        return {"open": fav, "blocked": blocked, "open_houses": open_h, "viparita": vip_count >= 3}

    def raja_yoga_pairs(self) -> list[str]:
        pairs = [
            ("Atmakarak", "Amatyakarak"), ("Atmakarak", "Putrakaraka"), ("Atmakarak", "Darakaraka"),
            ("Atmakarak", "_5th"), ("Amatyakarak", "Putrakaraka"), ("Amatyakarak", "Darakaraka"),
            ("Amatyakarak", "_5th"), ("Putrakaraka", "Darakaraka"), ("Putrakaraka", "_5th"),
            ("Darakaraka", "_5th"),
        ]
        hits = []
        fl_sign = sign_at(self.lagna, 5)
        for a, b in pairs:
            if b == "_5th":
                sa = self.role(a).get("sign")
                sb = fl_sign
                bl = self.fifth_lord
                label_b = f"5th lord {bl}"
            else:
                sa = self.role(a).get("sign")
                sb = self.role(b).get("sign")
                label_b = f"{ROLE_SHORT.get(b, b)} ({self.role(b).get('planet', '')})"
            if not sa or not sb:
                continue
            if sa == sb or mutual_sign_aspect(sa, sb):
                hits.append(
                    f"{ROLE_SHORT.get(a, a)} ({self.role(a).get('planet', '')}) + {label_b}: "
                    f"conjunction or mutual sign aspect."
                )
        return hits
