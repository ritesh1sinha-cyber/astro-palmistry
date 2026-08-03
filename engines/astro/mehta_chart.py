#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mehta Modern Techniques chart object (rules4)."""
from __future__ import annotations

from mehta_book_data import GROUP_I, GROUP_II, SIGNS, SIGN_LORD, house_of

KENDRA = {1, 4, 7, 10}
TRIKONA = {1, 5, 9}
UPACHAYA = {3, 6, 10, 11}
BENEFICS = {"Jupiter", "Venus", "Mercury", "Moon"}
MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
STRONG = {"exalted", "own_sign", "moolatrikona", "great_friend_sign"}
WEAK = {"debilitated", "enemy_sign"}
MOVABLE = {"Aries", "Cancer", "Libra", "Capricorn"}
FIXED = {"Taurus", "Leo", "Scorpio", "Aquarius"}
DUAL = {"Gemini", "Virgo", "Sagittarius", "Pisces"}
FIRE = {"Aries", "Leo", "Sagittarius"}
EARTH = {"Taurus", "Virgo", "Capricorn"}
AIR = {"Gemini", "Libra", "Aquarius"}
WATER = {"Cancer", "Scorpio", "Pisces"}


class MehtaChart:
    def __init__(self, pc: dict, book: dict):
        self.pc = pc
        self.book = book
        self.lagna = pc["meta"]["lagna_sign"]
        self.lagna_idx = SIGNS.index(self.lagna)
        self.name = pc["meta"]["client"]
        self.age = int(pc["meta"]["age"])
        self.moon_sign = pc["planets"]["Moon"]["sign"]
        self.sun_sign = pc["planets"]["Sun"]["sign"]
        self.moon_nak = pc["planets"]["Moon"].get("nakshatra", "")
        self.planets: dict = {}
        for nm, v in pc["planets"].items():
            self.planets[nm] = {
                "sign": v["sign"],
                "house": house_of(v["sign"], self.lagna),
                "dignity": v.get("dignity", "neutral_sign"),
                "nakshatra": v.get("nakshatra", ""),
                "retro": bool(v.get("retrograde", False)),
                "navamsha": v.get("navamsha_sign", ""),
            }
        self.rules: dict[str, list[int]] = {p: [] for p in self.planets}
        self.houses: dict[int, dict] = {}
        for h in range(1, 13):
            sign = SIGNS[(self.lagna_idx + h - 1) % 12]
            lord = SIGN_LORD[sign]
            self.houses[h] = {
                "sign": sign,
                "lord": lord,
                "tenants": [nm for nm, pl in self.planets.items() if pl["sign"] == sign],
            }
            if lord in self.rules:
                self.rules[lord].append(h)
        self.cur_md = pc["vimshottari"]["current_md"]
        self.antars = pc["vimshottari"]["current_md_antardashas"]

    def moon_house_from_lagna(self) -> int:
        return house_of(self.moon_sign, self.lagna)

    def wealth_from_moon(self) -> int:
        return house_of(SIGNS[(SIGNS.index(self.moon_sign) + 1) % 12], self.moon_sign)

    def sign_majority(self) -> dict[str, int]:
        counts = {"movable": 0, "fixed": 0, "dual": 0, "fire": 0, "earth": 0, "air": 0, "water": 0}
        for pl in self.planets:
            if pl in ("Rahu", "Ketu"):
                continue
            s = self.planets[pl]["sign"]
            if s in MOVABLE:
                counts["movable"] += 1
            if s in FIXED:
                counts["fixed"] += 1
            if s in DUAL:
                counts["dual"] += 1
            if s in FIRE:
                counts["fire"] += 1
            if s in EARTH:
                counts["earth"] += 1
            if s in AIR:
                counts["air"] += 1
            if s in WATER:
                counts["water"] += 1
        return counts

    def navamsha_dilution_flags(self) -> list[str]:
        flags: list[str] = []
        for pl, info in self.planets.items():
            if pl in ("Rahu", "Ketu"):
                continue
            nav = info.get("navamsha") or ""
            if not nav:
                continue
            d1_strong = info["dignity"] in STRONG
            nav_dignity = self.pc["planets"].get(pl, {}).get("navamsha_dignity", "")
            if d1_strong and nav_dignity in WEAK:
                flags.append(
                    f"{pl} strong in rashi but weak in Navamsha ({nav}) - Mehta: delivery diluted."
                )
            elif info["dignity"] in WEAK and nav_dignity in STRONG:
                flags.append(
                    f"{pl} weak in rashi but strengthened in Navamsha ({nav}) - cancellation theme."
                )
        return flags

    def detect_mehta_yogas(self) -> list[dict]:
        found: list[dict] = []
        pl = self.planets

        kendra_lords = {self.houses[h]["lord"] for h in KENDRA}
        trikona_lords = {self.houses[h]["lord"] for h in TRIKONA}
        for kl in kendra_lords:
            for tl in trikona_lords:
                if kl == tl:
                    continue
                if pl[kl]["sign"] == pl[tl]["sign"] or abs(pl[kl]["house"] - pl[tl]["house"]) in (0, 6):
                    found.append({
                        "name": f"Kendra-Trikona link ({kl}-{tl})",
                        "result": "Among Mehta's strongest raja yoga patterns when both lords are strong.",
                    })
                    break

        g1 = {self.houses[h]["lord"] for h in GROUP_I}
        g2 = {self.houses[h]["lord"] for h in GROUP_II}
        for a in g1:
            for b in g2:
                if a == b:
                    continue
                if pl[a]["sign"] == pl[b]["sign"]:
                    found.append({
                        "name": f"Group I + Group II lord mix ({a}-{b})",
                        "result": "Mehta: good lord with trika lord - daridra-type stress on wealth unless mitigated.",
                    })
                    break

        g2_sigs = [self.houses[h]["lord"] for h in GROUP_II]
        for i, a in enumerate(g2_sigs):
            for b in g2_sigs[i + 1:]:
                if a == b:
                    continue
                if pl[a]["sign"] == pl[b]["sign"]:
                    found.append({
                        "name": f"Viparita cluster ({a}+{b})",
                        "result": "Group II lords combining - viparita raja yoga wealth potential after struggle.",
                    })

        malefic_kendras = [
            p for p in MALEFICS
            if pl[p]["house"] in KENDRA and pl[p]["dignity"] not in STRONG
        ]
        if malefic_kendras:
            found.append({
                "name": "Malefics in kendras (unmitigated)",
                "result": f"{', '.join(malefic_kendras)} in kendra without full strength - peace, marriage, or property strain.",
            })

        benefic_up = [p for p in BENEFICS if pl[p]["house"] in UPACHAYA]
        malefic_up = [p for p in MALEFICS if pl[p]["house"] in UPACHAYA]
        if len(benefic_up) >= 2 and len(malefic_up) >= 2:
            found.append({
                "name": "Benefics in kendras + malefics in upachaya",
                "result": "Classic Mehta rise pattern: benefics anchor, malefics in 3/6/11 give competitive lift.",
            })

        ll = self.houses[1]["lord"]
        if pl[ll]["dignity"] in STRONG and pl["Moon"]["dignity"] in STRONG and pl["Sun"]["dignity"] in STRONG:
            found.append({
                "name": "Lagna + Moon + Sun tripod",
                "result": "K.N. Rao emphasis in Mehta foreword: powerful chart, recognition, possible international fame.",
            })

        ven = pl["Venus"]
        if ven["house"] == 7 and ven["dignity"] == "exalted":
            found.append({
                "name": "Exalted Venus as 7th karaka",
                "result": "Strongest wife/happiness indicator in Mehta seventh-house chapter.",
            })

        return found[:8]
