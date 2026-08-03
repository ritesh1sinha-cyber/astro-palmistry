#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BNN whole-sign chart + Vimshottari timing from precompute."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Optional

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
    "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]
SIGN_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}
STRONG = ("exalted", "own_sign", "moolatrikona", "great_friend_sign")
WEAK = ("debilitated", "enemy_sign")

BODY = {
    "Aries": "head, brain, and nervous tension", "Taurus": "face, throat, neck, and thyroid",
    "Gemini": "shoulders, arms, lungs, and breath", "Cancer": "chest, stomach, and digestion",
    "Leo": "heart, spine, and circulation", "Virgo": "intestines, gut, and assimilation",
    "Libra": "kidneys, lower back, and fluid balance", "Scorpio": "reproductive and excretory systems",
    "Sagittarius": "hips, thighs, and the liver", "Capricorn": "knees, bones, joints, and skin",
    "Aquarius": "calves, ankles, and circulation", "Pisces": "feet, lymph, and immunity",
}


def house_of(sign: str, lagna: str) -> int:
    return (SIGNS.index(sign) - SIGNS.index(lagna)) % 12 + 1


def sign_in_house(h: int, lagna: str) -> str:
    return SIGNS[(SIGNS.index(lagna) + h - 1) % 12]


def fmt_date(iso: Optional[str]) -> str:
    if not iso:
        return "-"
    try:
        return datetime.strptime(iso[:10], "%Y-%m-%d").strftime("%d %b %Y").lstrip('0')
    except Exception:
        return str(iso)


def pd(iso: str) -> date:
    return datetime.strptime(iso[:10], "%Y-%m-%d").date()


class BnnChart:
    def __init__(self, pc: dict, client_name: str = ""):
        self.pc = pc
        self.lagna = pc["meta"]["lagna_sign"]
        self.name = client_name or pc["meta"]["client"]
        self.planets = {}
        for nm, v in pc["planets"].items():
            sign = v["sign"]
            self.planets[nm] = {
                "sign": sign, "house": house_of(sign, self.lagna),
                "dignity": v.get("dignity", "neutral_sign"),
                "nakshatra": v.get("nakshatra", ""), "pada": v.get("pada", ""),
                "retrograde": bool(v.get("retrograde", False)),
            }
        self.by_sign: dict[str, list[str]] = {}
        for nm, v in self.planets.items():
            self.by_sign.setdefault(v["sign"], []).append(nm)
        self.conjunctions = {s: ps for s, ps in self.by_sign.items() if len(ps) > 1}

    def h(self, planet: str) -> int:
        return self.planets[planet]["house"]

    def sign(self, planet: str) -> str:
        return self.planets[planet]["sign"]

    def dig(self, planet: str) -> str:
        return self.planets[planet]["dignity"]

    def in_house(self, n: int) -> list[str]:
        return [p for p, v in self.planets.items() if v["house"] == n]

    def lord_of_house(self, n: int) -> str:
        return SIGN_LORD[sign_in_house(n, self.lagna)]

    def house_sign(self, n: int) -> str:
        return sign_in_house(n, self.lagna)

    def conj_with(self, planet: str) -> list[str]:
        return [p for p in self.by_sign.get(self.sign(planet), []) if p != planet]

    def houses_ruled(self, lord: str) -> list[int]:
        if lord not in self.planets or lord in ("Rahu", "Ketu"):
            return []
        return [n for n in range(1, 13) if self.lord_of_house(n) == lord]

    def atmakaraka(self) -> str:
        for k in self.pc.get("cara_karakas", {}).get("karakas", []):
            if k.get("role") == "Atmakarak":
                return k.get("planet", "")
        return ""

    def has_pair(self, a: str, b: str) -> bool:
        return b in self.conj_with(a) or a in self.conj_with(b)


class BnnTiming:
    def __init__(self, ch: BnnChart, pc: dict):
        self.pc = pc
        self.ch = ch
        self.age = int(pc["meta"].get("age", 0))
        vim = pc.get("vimshottari", {})
        self.seq = vim.get("sequence", [])
        self.cur_md = vim.get("current_md", {})
        self.antars = vim.get("current_md_antardashas", [])

    def antar_windows(self) -> list[dict]:
        out = []
        for a in self.antars:
            out.append({
                "lord": a["ad_lord"],
                "start": pd(a["start"]),
                "end": pd(a["end"]),
                "status": a.get("status", ""),
                "md": self.cur_md.get("md_lord", ""),
            })
        return out

    def current_antar(self) -> dict:
        return next((a for a in self.antars if a.get("status") == "current"), {})

    def future_antars(self, n: int = 4) -> list[dict]:
        return [a for a in self.antars if a.get("status") == "future"][:n]


def load_bnn_chart(
    extracted_path: str = "",
    client_name: str = "",
    dob: str = "",
    pc: dict | None = None,
) -> tuple[BnnChart, BnnTiming]:
    if pc is None:
        from astro_precompute import precompute
        if not extracted_path:
            raise ValueError("load_bnn_chart needs pc or extracted_path")
        pc = precompute(extracted_path, client_name, dob)
    ch = BnnChart(pc, client_name)
    return ch, BnnTiming(ch, pc)


def lord_verdict(ch: BnnChart, p: str) -> str:
    pl = ch.planets.get(p, {})
    dig = pl.get("dignity", "neutral_sign")
    occ = pl.get("house", 1)
    if dig in STRONG or occ in (1, 4, 5, 9, 10, 11):
        return "good"
    if dig in WEAK or occ in (6, 8, 12):
        return "amber"
    return "neutral"
