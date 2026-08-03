#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared chart-generic BNN phrasing (book lookups + placement facts)."""
from __future__ import annotations

import html
from typing import TYPE_CHECKING

from bnn_book_data import (
    house_from_jupiter,
    humanize_bnn,
    load_bnn_book,
    lookup_from_jupiter,
    lookup_node_in_house,
    lookup_planet_sign,
    lookup_profession_sign,
)
from bnn_chart import BODY, SIGN_LORD, lord_verdict

if TYPE_CHECKING:
    from bnn_chart import BnnChart, BnnTiming

HOUSE_THEME = {
    1: "self and vitality",
    2: "wealth, speech, and family line",
    3: "siblings, courage, and short journeys",
    4: "home, mother, and emotional roots",
    5: "children, creativity, and intelligence",
    6: "health, service, and daily work",
    7: "marriage and open partnerships",
    8: "shared resources, change, and hidden matters",
    9: "dharma, father, fortune, and long journeys",
    10: "career, status, and public name",
    11: "gains, networks, and fulfilment of wishes",
    12: "loss, retreat, and foreign or spiritual life",
}

DIGNITY_WORD = {
    "exalted": "exalted",
    "debilitated": "debilitated",
    "own_sign": "in own sign",
    "moolatrikona": "in moolatrikona",
    "great_friend_sign": "in a friendly sign",
    "enemy_sign": "in an enemy sign",
    "neutral_sign": "neutral dignity",
}


def esc(s: str) -> str:
    return html.escape(str(s))


def dignity_phrase(dig: str) -> str:
    return DIGNITY_WORD.get(dig, dig.replace("_", " "))


def karaka_planet(ch: "BnnChart", role: str) -> str:
    for k in ch.pc.get("cara_karakas", {}).get("karakas", []):
        if k.get("role") == role:
            return k.get("planet", "")
    return ""


def karaka_row(ch: "BnnChart", role: str) -> dict | None:
    for k in ch.pc.get("cara_karakas", {}).get("karakas", []):
        if k.get("role") == role:
            return k
    return None


def placement_fact(ch: "BnnChart", planet: str) -> str:
    if planet not in ch.planets:
        return planet
    v = ch.planets[planet]
    bits = [f"{planet} in {v['sign']} (house {v['house']})"]
    dig = dignity_phrase(v["dignity"])
    if dig != "neutral dignity":
        bits.append(dig)
    ruled = ch.houses_ruled(planet)
    if ruled:
        bits.append(f"rules {', '.join(str(h) for h in ruled)}")
    return " | ".join(bits)


def lord_line(ch: "BnnChart", house_n: int) -> str:
    lord = ch.lord_of_house(house_n)
    sign = ch.house_sign(house_n)
    if lord not in ch.planets:
        return f"{house_n}th {sign} - lord {lord}"
    return (
        f"{house_n}th {sign} - lord {lord} in {ch.sign(lord)} "
        f"(house {ch.h(lord)}, {dignity_phrase(ch.dig(lord))})"
    )


def book_planet_sign(ch: "BnnChart", planet: str, direction: str = "neutral") -> str:
    book = load_bnn_book()
    if planet not in ch.planets:
        return ""
    return humanize_bnn(
        lookup_planet_sign(book, planet, ch.sign(planet), ch.dig(planet), direction)
    )


def book_clause(*parts: str, max_n: int = 3) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for p in parts:
        p = (p or "").strip()
        if not p or p in seen:
            continue
        seen.add(p)
        out.append(p)
        if len(out) >= max_n:
            break
    return out


def stellium_houses(ch: "BnnChart", min_n: int = 3) -> list[tuple[int, list[str]]]:
    by_h: dict[int, list[str]] = {}
    for p, v in ch.planets.items():
        by_h.setdefault(v["house"], []).append(p)
    return sorted(
        [(h, ps) for h, ps in by_h.items() if len(ps) >= min_n],
        key=lambda x: -len(x[1]),
    )


def traffic_class(tone: str) -> str:
    return {"good": "traffic-green", "amber": "traffic-amber"}.get(tone, "traffic-neutral")


def antar_chart_note(ch: "BnnChart", lord: str) -> str:
    if lord not in ch.planets:
        return f"{lord} antardasha"
    ruled = ch.houses_ruled(lord)
    ruled_txt = f", rules houses {', '.join(str(h) for h in ruled)}" if ruled else ""
    return (
        f"{lord} in {ch.sign(lord)} (house {ch.h(lord)}, {dignity_phrase(ch.dig(lord))}){ruled_txt}"
    )


def antar_unload(ch: "BnnChart", lord: str) -> str:
    book = load_bnn_book()
    clauses = book_clause(
        book_planet_sign(ch, lord),
        humanize_bnn(lookup_from_jupiter(book, lord, house_from_jupiter(ch.sign("Jupiter"), ch.sign(lord))))
        if "Jupiter" in ch.planets and lord in ch.planets
        else "",
        max_n=2,
    )
    if clauses:
        return " ".join(clauses)
    h = ch.h(lord) if lord in ch.planets else 0
    return f"Work the {HOUSE_THEME.get(h, f'house {h}')} themes sincerely while {lord} runs this sub-period."


def conjunction_pairs(ch: "BnnChart") -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for _sign, ps in ch.conjunctions.items():
        if len(ps) < 2:
            continue
        key = tuple(sorted((ps[0], ps[1])))
        if key in seen:
            continue
        seen.add(key)
        pairs.append((ps[0], ps[1]))
    return pairs


def intro_stack(ch: "BnnChart", bt: "BnnTiming") -> str:
    ll = SIGN_LORD[ch.lagna]
    bits = [f"{ch.lagna} lagna - {ll} ({dignity_phrase(ch.dig(ll))}) in the {ch.h(ll)}th"]
    for a, b in conjunction_pairs(ch)[:2]:
        bits.append(f"{a}-{b} together in the {ch.h(a)}th ({ch.sign(a)})")
    ak = ch.atmakaraka() or karaka_planet(ch, "Atmakarak")
    if ak:
        bits.append(f"Atmakaraka {ak} in the {ch.h(ak)}th")
    md = bt.cur_md.get("md_lord", "")
    cur = bt.current_antar()
    if md and cur.get("ad_lord"):
        bits.append(
            f"running {md} mahadasha / {cur['ad_lord']} antar until {cur.get('end', '')[:10]}"
        )
    return " | ".join(bits)
