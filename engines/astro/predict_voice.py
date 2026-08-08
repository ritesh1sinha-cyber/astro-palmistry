"""Prediction-first copy — real-life scenario + one compressed backing line.

Every customer-facing block should come through here (or palm_voice for palms).
Engine modules keep returning structured facts; this module turns them into
plain predictions a layperson can act on.
"""

from __future__ import annotations

import html as _html
import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Optional

from report_language import normalize_sentence_dashes

# ---------------------------------------------------------------------------
# Area headlines — moved from report_cards.CLAIMS (prediction voice)
# ---------------------------------------------------------------------------
AREA_SCENE: dict[tuple[str, str], str] = {
    ("career", "up"): (
        "Your work gets seen. This is a period where effort converts into position."
    ),
    ("career", "mixed"): (
        "The work is solid; the recognition is slower than the work. Both are true at once."
    ),
    ("career", "down"): (
        "Recognition lags behind what you are actually delivering. "
        "This is a build phase, not a reward phase."
    ),
    ("money", "up"): "Money arrives more easily than usual, and more of it stays.",
    ("money", "mixed"): (
        "Income holds, but it leaks. What you keep matters more than what you earn right now."
    ),
    ("money", "down"): (
        "Money is tight relative to the effort. Protect what exists before chasing more."
    ),
    ("love", "up"): "Your closest relationship steadies and deepens through this stretch.",
    ("love", "mixed"): (
        "Warmth is there, but so is friction. "
        "This is a period that rewards saying the awkward thing early."
    ),
    ("love", "down"): (
        "Distance shows up in your closest relationship. "
        "Usually as silence rather than argument."
    ),
    ("home", "up"): "Home becomes the steady base you work from.",
    ("home", "mixed"): "Home is mostly settled, with one recurring pull on your attention.",
    ("home", "down"): "Something at home takes more of you than you have been admitting.",
    ("children", "up"): (
        "Children and creative work both go well — the same part of your chart runs them."
    ),
    ("children", "mixed"): (
        "Progress with children is real but uneven; patience does more than pressure."
    ),
    ("children", "down"): "A worry about a child sits in the background of this period.",
    ("health", "up"): "Your energy holds well. Your body recovers faster than you expect.",
    ("health", "mixed"): (
        "Energy is adequate but not abundant. Sleep is the variable that decides the rest."
    ),
    ("health", "down"): (
        "Your energy runs lower than your schedule assumes. This is the area to protect first."
    ),
    ("learning", "up"): "Study, teachers and the right introductions all come easily now.",
    ("learning", "mixed"): "Opportunity comes, but through effort rather than luck.",
    ("learning", "down"): (
        "Doors open slower than they should. Ask directly rather than waiting to be noticed."
    ),
    ("inner", "up"): "You have unusual clarity about what actually matters to you.",
    ("inner", "mixed"): "A quiet restlessness runs under the surface of this period.",
    ("inner", "down"): (
        "Rest is not optional in this stretch. Withdrawal is doing something, not avoiding it."
    ),
    ("legal", "up"): (
        "The chart favours a resolution in your direction — a good stretch to press "
        "the matter rather than let it sit."
    ),
    ("legal", "mixed"): (
        "The matter moves, but slowly, with some give-and-take on both sides."
    ),
    ("legal", "down"): (
        "This is not the strongest stretch for a legal matter. Protect your "
        "position and avoid escalating further right now."
    ),
}

AREA_LABEL = {
    "career": "work and career",
    "money": "money",
    "love": "your closest relationship",
    "home": "home and family",
    "children": "children",
    "health": "your health and energy",
    "learning": "study and luck",
    "inner": "your inner life",
    "legal": "your legal matter",
}

VARGA_PLAIN = {
    "career": "career chart",
    "money": "wealth chart",
    "love": "marriage chart",
    "home": "home chart",
    "children": "children chart",
    "health": "health chart",
    "learning": "learning chart",
    "inner": "spiritual chart",
}

VARGA_FOCUS_PLAIN = {
    "career": "career and public standing",
    "money": "savings and what you accumulate",
    "love": "marriage and partnership",
    "home": "property, family roots and domestic peace",
    "children": "children and creative legacy",
    "health": "vitality and recurring health patterns",
    "learning": "study, teachers and grasp of subjects",
    "inner": "faith and inner growth",
}

VARGA_STRENGTH = {
    "strong": "well-built",
    "mixed": "workable",
    "weak": "under strain",
}

DIGNITY_WORD = {
    "exalted": "strong",
    "moolatrikona": "strong",
    "own_sign": "strong",
    "own sign": "strong",
    "friendly_sign": "comfortable",
    "friend": "comfortable",
    "neutral_sign": "mixed",
    "neutral": "mixed",
    "enemy_sign": "strained",
    "enemy": "strained",
    "debilitated": "weak",
}

# What the running sub-period lord feels like in real life
LORD_SCENE: dict[tuple[str, str], str] = {
    ("Sun", "up"): (
        "You are being watched and measured by a boss, a parent, or your own standards. "
        "Visibility is the theme."
    ),
    ("Sun", "mixed"): (
        "You want credit for work already done, but the room is not fully paying attention yet."
    ),
    ("Sun", "down"): (
        "Effort is visible to you but not to the people who decide. Patience beats pushing."
    ),
    ("Moon", "up"): (
        "Home and mood settle when you protect sleep and routine. "
        "The people close to you matter more than the agenda."
    ),
    ("Moon", "mixed"): (
        "Emotional weather at home. You carry more than you show. "
        "Small frictions land harder than they should."
    ),
    ("Moon", "down"): (
        "Restlessness at home and in your chest, even when nothing is objectively wrong."
    ),
    ("Mars", "up"): (
        "You have drive to push through friction. Finish what you started before escalating."
    ),
    ("Mars", "mixed"): (
        "Friction and effort. Something will not move until you stop forcing the wrong lever."
    ),
    ("Mars", "down"): (
        "Conflict costs more than it wins right now. Let the other side move first."
    ),
    ("Mercury", "up"): (
        "Talks, paperwork and negotiation open doors. Put agreements in writing."
    ),
    ("Mercury", "mixed"): (
        "Conversations and paperwork will not settle until you chase the loose thread."
    ),
    ("Mercury", "down"): (
        "Misunderstandings sit in the wording, not the intent. Slow down before you sign."
    ),
    ("Jupiter", "up"): (
        "Doors open partway. Ask someone senior to speak for you. Sponsorship matters now."
    ),
    ("Jupiter", "mixed"): (
        "Expansion and advice arrive, but not on your timeline. Keep showing up."
    ),
    ("Jupiter", "down"): (
        "Promises outrun delivery. Verify before you commit."
    ),
    ("Venus", "up"): (
        "Relationships and comfort improve when you repair goodwill before asking."
    ),
    ("Venus", "mixed"): (
        "You weigh what you are willing to spend, money or energy, for comfort and peace."
    ),
    ("Venus", "down"): (
        "Pleasure and partnership need repair before they reward you."
    ),
    ("Saturn", "up"): (
        "Slow, verifiable work converts. Finish the boring part. That is what unlocks this."
    ),
    ("Saturn", "mixed"): (
        "Weight and delay. Doing unglamorous work with no applause. That is the point."
    ),
    ("Saturn", "down"): (
        "Half-done work stalls at review. Discipline beats speed."
    ),
    ("Rahu", "up"): (
        "Ambition pulls toward something unfamiliar. Verify what looks too convenient."
    ),
    ("Rahu", "mixed"): (
        "Restlessness. Wanting something not quite in reach. Go steady and avoid haste."
    ),
    ("Rahu", "down"): (
        "Obsession without payoff. Step back before you overcommit."
    ),
    ("Ketu", "up"): (
        "Detachment clears noise. What falls away was costing you attention."
    ),
    ("Ketu", "mixed"): (
        "Losing interest in something you used to care about. That can be healthy."
    ),
    ("Ketu", "down"): (
        "Withdrawal feels like failure but may be protection. Rest without guilt."
    ),
}

RELIEF = {
    "fav": "This window stays open and supportive.",
    "mix": "Mixed signals. Patience over big moves.",
    "chal": "This eases when you stop forcing outcomes.",
}

TRANSIT_SUPPORT = {
    True: "well supported",
    False: "more pressure than payoff",
}


@dataclass
class Prediction:
    scenario: str
    backing: str
    direction: str = "mixed"

    def html(self, *, esc: bool = True) -> str:
        """Two-part block: scenario paragraph + Why line."""
        s = _html.escape(self.scenario) if esc else self.scenario
        b = _html.escape(self.backing) if esc else self.backing
        return (
            f'<div class="prediction" data-verdict="{_html.escape(self.direction)}">'
            f'<p class="pred-scenario">{s}</p>'
            f'<p class="pred-why"><b>Why:</b> {b}</p></div>'
        )


def _ord(n: Any) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ""
    return f"{n}" + ("th" if 10 <= n % 100 <= 20
                     else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


def _pretty(d: Optional[date]) -> str:
    return f"{d:%B %Y}" if d else ""


def _dignity_word(code: str) -> str:
    return DIGNITY_WORD.get((code or "").lower().replace(" ", "_"), "mixed")


def polish_prose(text: str) -> str:
    return normalize_sentence_dashes((text or "").strip())


def _varga_scenario(area_key: str, direction: str, varga: dict) -> str:
    """One divisional-chart sentence unique to this life area."""
    if not varga:
        return ""
    chart = VARGA_PLAIN.get(area_key, "specialised chart")
    focus = VARGA_FOCUS_PLAIN.get(area_key, "this life area")
    strength = varga.get("strength", "mixed")
    field_lord = varga.get("field_lord") or varga.get("ruler", "")
    fld = _dignity_word(varga.get("field_lord_dignity") or varga.get("ruler_dignity", ""))
    fh = varga.get("field_lord_house") or varga.get("ruler_house")
    strong = varga.get("strong_planets") or []
    karaka = varga.get("karaka", "")
    kar_dig = _dignity_word(varga.get("karaka_dignity", ""))
    ben = varga.get("benefics_in_field") or []
    mal = varga.get("malefics_in_field") or []

    parts: list[str] = []
    if field_lord and fld in ("strong", "comfortable"):
        parts.append(
            f"Your {chart} backs {focus} through {field_lord}, "
            f"strong where it counts."
        )
    elif field_lord and fld == "weak":
        parts.append(
            f"Your {chart} flags {field_lord} weak on {focus}. "
            f"Steady effort matters more than speed."
        )
    elif field_lord and fld == "strained":
        parts.append(
            f"Your {chart} puts {field_lord} under strain on {focus}. "
            f"Do not force outcomes here."
        )
    elif strength == "strong":
        parts.append(f"Your {chart} is well-built for {focus}.")
    elif strength == "weak":
        parts.append(f"Your {chart} runs under strain on {focus}.")
    else:
        parts.append(f"Your {chart} is workable on {focus}, but not automatic.")

    if karaka and kar_dig in ("strong", "comfortable") and direction == "up":
        parts.append(f"{karaka} adds extra backing there.")
    elif karaka and kar_dig == "weak" and direction == "down":
        parts.append(f"{karaka}, the natural marker here, sits weak in this chart.")
    elif ben and direction != "down":
        parts.append(f"{ben[0]} protects this area in the {chart}.")
    elif mal and direction == "down":
        parts.append(f"{mal[0]} presses on {focus} in the {chart}.")
    elif strong and direction == "up":
        if len(strong) == 1:
            parts.append(f"{strong[0]} strengthens the {chart}.")
        else:
            parts.append(f"{', '.join(strong[:2])} strengthen the {chart}.")

    if fh and direction == "mixed":
        parts.append(f"The ruler sits in your {_ord(fh)} house in that chart.")

    return " ".join(parts[:2])


def _backing(*, md_lord: str = "", ad_lord: str = "", house: int = 0,
             lord: str = "", dignity: str = "", lord_house: Any = None,
             transits: Optional[list] = None, varga_area: str = "",
             varga_strength: str = "", varga: Optional[dict] = None,
             houses_supported: Optional[list] = None,
             planet_strengths: Optional[list] = None,
             max_len: int = 220) -> str:
    """One compressed line — semicolon-separated clauses, capped."""
    parts: list[str] = []
    varga = varga or {}

    if md_lord and ad_lord and house:
        parts.append(
            f"{md_lord}–{ad_lord} period activates your {_ord(house)} house")
    elif ad_lord and house:
        parts.append(f"{ad_lord} period runs through your {_ord(house)} house")
    elif lord and house:
        parts.append(f"{lord} rules your {_ord(house)} house")

    if lord and dignity:
        parts.append(f"{lord} {_dignity_word(dignity)}")
    if lord_house:
        try:
            lh = int(lord_house)
            parts.append(f"{lord or 'ruler'} placed in the {_ord(lh)} house")
        except (TypeError, ValueError):
            pass

    for t in (transits or [])[:2]:
        planet = t.get("planet", "")
        h = t.get("house")
        bav = t.get("bav", 0)
        if planet and h:
            sup = TRANSIT_SUPPORT.get((bav or 0) >= 5, "mixed")
            parts.append(f"{planet} crossing your {_ord(h)} house ({sup})")

    if houses_supported:
        hs = ", ".join(_ord(h) for h in houses_supported[:3])
        parts.append(f"houses {hs} supported")

    plain = VARGA_PLAIN.get(varga_area, "specialised chart")
    if varga_area and (varga or varga_strength):
        field_lord = varga.get("field_lord") or varga.get("ruler", "")
        fld = varga.get("field_lord_dignity") or varga.get("ruler_dignity", "")
        fh = varga.get("field_lord_house") or varga.get("ruler_house")
        strength = varga.get("strength") or varga_strength or "mixed"
        strong = varga.get("strong_planets") or []
        clause = plain
        if field_lord:
            clause += f": {field_lord} {_dignity_word(fld)}"
            if fh:
                clause += f" in {_ord(fh)} house"
        else:
            clause += f" {VARGA_STRENGTH.get(strength, 'workable')}"
        if strong:
            clause += f"; strong {', '.join(strong[:2])}"
        parts.append(clause)

    if planet_strengths:
        parts.append(", ".join(planet_strengths[:4]))

    line = "; ".join(p for p in parts if p)
    if len(line) > max_len:
        line = line[: max_len - 1].rsplit(";", 1)[0] + "…"
    return line or "your chart points here from several independent reads"


def compose(area_key: str, *, direction: str = "mixed",
            md_lord: str = "", ad_lord: str = "",
            house: int = 0, lord: str = "", dignity: str = "",
            lord_house: Any = None, transits: Optional[list] = None,
            varga_strength: str = "", varga: Optional[dict] = None,
            window_rating: str = "",
            window_end: Optional[date] = None,
            period_feeling: str = "",
            extra_scenario: str = "",
            include_period_lord: bool = False) -> Prediction:
    """Build scenario + backing from structured facts (no engine prose)."""
    direction = direction if direction in ("up", "down", "mixed") else "mixed"
    varga = varga or {}
    area_line = AREA_SCENE.get((area_key, direction), "")
    lord_line = LORD_SCENE.get((ad_lord or md_lord, direction), "")

    scenario_parts = []
    if include_period_lord and lord_line:
        scenario_parts.append(lord_line)
    if area_line:
        scenario_parts.append(area_line)
    varga_line = _varga_scenario(area_key, direction, varga)
    if varga_line:
        scenario_parts.append(varga_line)
    if extra_scenario:
        scenario_parts.append(extra_scenario.strip())
    if period_feeling and not include_period_lord:
        scenario_parts.append(period_feeling)

    relief = RELIEF.get(window_rating, "")
    if window_end and relief:
        scenario_parts.append(f"{relief.rstrip('.')}. after {_pretty(window_end)}.")
    elif relief:
        scenario_parts.append(relief + ".")

    scenario = polish_prose(" ".join(scenario_parts).strip())
    if not scenario:
        label = AREA_LABEL.get(area_key, area_key)
        scenario = f"Your chart is {direction} on {label} through this stretch."

    backing = polish_prose(_backing(
        md_lord=md_lord, ad_lord=ad_lord, house=house, lord=lord,
        dignity=dignity, lord_house=lord_house, transits=transits,
        varga_area=area_key, varga_strength=varga_strength or varga.get("strength", ""),
        varga=varga))

    return Prediction(scenario=scenario, backing=backing, direction=direction)


def compose_period(pc: dict, *, today: Optional[date] = None,
                   direction: str = "mixed") -> Prediction:
    """Opening period block only — uses running sub-period lord voice."""
    today = today or date.today()
    import report_confluence as CF

    now = CF.vimshottari_at(pc, today)
    md_lord = now.get("md", "")
    ad_lord = now.get("ad", "")
    dasha = CF.dasha_confluence(pc, today)
    direction = dasha.get("direction", direction)
    if direction not in ("up", "down", "mixed"):
        direction = "mixed"

    planets = pc.get("planets", {}) or {}
    hl = pc.get("house_lords", {}) or {}

    def houses_of(lord: str) -> list:
        if not lord:
            return []
        out = [int(h) for h, v in hl.items() if v.get("lord") == lord]
        sits = (planets.get(lord) or {}).get("house")
        if sits:
            out.append(int(sits))
        return sorted(set(out))

    active = houses_of(ad_lord) or houses_of(md_lord)
    feel = LORD_SCENE.get((ad_lord, direction), "") or LORD_SCENE.get((ad_lord, "mixed"), "")
    chapter = {"up": "a supportive chapter", "down": "a demanding chapter"}.get(
        direction, "a mixed chapter")
    parts = [f"You are in a {md_lord}–{ad_lord} stretch."]
    if feel:
        parts.append(feel)
    parts.append(f"This is {chapter}.")
    scenario = polish_prose(" ".join(parts))
    backing = polish_prose(_backing(
        md_lord=md_lord, ad_lord=ad_lord,
        house=active[0] if active else 0))
    return Prediction(scenario=scenario, backing=backing, direction=direction)


def compose_from_area(pc: dict, area_key: str, house: int, *,
                      today: Optional[date] = None,
                      transits: Optional[list] = None) -> Prediction:
    """Gather facts from precompute + confluence, return a Prediction."""
    today = today or date.today()
    import report_confluence as CF

    verdict = CF.area_verdict(pc, area_key, house)
    hl = (pc.get("house_lords", {}) or {}).get(str(house)) or {}
    lord = hl.get("lord", "")
    dignity = str(hl.get("lord_dignity") or "")
    lord_house = hl.get("lord_house")

    now = CF.vimshottari_at(pc, today)
    md_lord = now.get("md", "")
    ad_lord = now.get("ad", "")

    varga: dict = {}
    varga_strength = "mixed"
    window_rating = "mix"
    window_end = None
    try:
        import deep_evidence as DE
        de = DE.for_area(area_key, house=house)
        varga = de.get("varga") or {}
        varga_strength = varga.get("strength", "mixed")
        cw = de.get("current_window") or {}
        window_rating = de.get("current_rating") or cw.get("rating") or "mix"
    except Exception:  # noqa: BLE001
        de = {}

    direction = verdict.get("direction", "mixed")
    return compose(
        area_key, direction=direction, md_lord=md_lord, ad_lord=ad_lord,
        house=house, lord=lord, dignity=dignity, lord_house=lord_house,
        transits=transits, varga_strength=varga_strength, varga=varga,
        window_rating=window_rating, window_end=window_end,
        include_period_lord=False)


def compose_present_period(pc: dict, *, today: Optional[date] = None,
                           active_houses: Optional[list] = None,
                           live_transits: Optional[list] = None) -> list:
    """Opening block: period line + one prediction per active house."""
    today = today or date.today()
    import report_confluence as CF

    now = CF.vimshottari_at(pc, today)
    md_lord = now.get("md", "")
    ad_lord = now.get("ad", "")
    blocks: list[tuple[str, Prediction]] = []

    if ad_lord:
        pred = compose_period(pc, today=today)
        blocks.append(("period", pred))

    house_area = {
        10: "career", 2: "money", 7: "love", 4: "home", 5: "children",
        1: "health", 9: "learning", 12: "inner", 6: "health",
        3: "career", 11: "money", 8: "health",
    }
    seen: set = set()
    for h in (active_houses or [])[:2]:
        area = house_area.get(int(h), "")
        if not area or area in seen:
            continue
        seen.add(area)
        house_transits = [t for t in (live_transits or []) if t.get("house") == h]
        pred = compose_from_area(
            pc, area, int(h), today=today, transits=house_transits)
        blocks.append((area, pred))

    return blocks


def transit_sentence(planet: str, house: int, since: date, until: date,
                     bav: int, life_theme: str) -> Prediction:
    """Single live transit as prediction + backing."""
    supported = (bav or 0) >= 5
    if supported:
        scenario = (
            f"{planet} has been activating {life_theme} since {_pretty(since)}. "
            f"This is a window where effort can convert. Use it before {_pretty(until)}."
        )
    else:
        scenario = (
            f"{planet} has been pressing on {life_theme} since {_pretty(since)}. "
            f"Go steady rather than force outcomes. This eases after {_pretty(until)}."
        )
    backing = (
        f"{planet} crossing your {_ord(house)} house ({TRANSIT_SUPPORT[supported]})"
    )
    direction = "up" if supported else "mixed"
    return Prediction(
        scenario=polish_prose(scenario), backing=polish_prose(backing), direction=direction)


def confidence_word(agreement_n: int = 0, agreement_total: int = 0,
                    direction: str = "mixed") -> str:
    """Replace 'N of M methods agree' with a single confidence word."""
    if agreement_total <= 0:
        return {"up": "strong read", "down": "demanding read",
                "mixed": "mixed read"}.get(direction, "mixed read")
    ratio = agreement_n / max(1, agreement_total)
    if ratio >= 0.75 and direction == "up":
        return "strong agreement"
    if ratio >= 0.6:
        return "moderate agreement"
    if direction == "mixed":
        return "split read"
    return "cautious read"
