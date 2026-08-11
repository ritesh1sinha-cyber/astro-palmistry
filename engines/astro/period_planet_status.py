"""Period-planet status chips for the confluence report opening.

Primary labels use lagna-functional status + D1 dignity/house strength.
When D9 (navamsha) or Jaimini (from karakamsa) disagree with D1, a short
confluence note is added — so “strong in birth chart, weak in Jaimini/D9”
is never silent.
"""
from __future__ import annotations

import html as _html
from datetime import date
from typing import Any, Optional


_FUNC_WORD = {
    "yogakaraka": "especially supportive",
    "functional_benefic": "supportive",
    "functional_malefic": "challenging",
    "maraka": "challenging",
    "neutral": "neutral",
    "unknown": "neutral",
}

_STRONG = frozenset({"exalted", "moolatrikona", "own_sign"})
_WEAK = frozenset({"debilitated", "enemy_sign"})
_DUSTHANA = frozenset({6, 8, 12})


def _e(t: Any) -> str:
    return _html.escape(str(t or ""))


def _dignity_code(dig: str) -> str:
    return (dig or "").lower().replace(" ", "_")


def _planet_row(pc: dict, planet: str) -> dict:
    return (pc.get("planets") or {}).get(planet) or {}


def _d1_sign(pc: dict, planet: str) -> str:
    return str(_planet_row(pc, planet).get("sign") or "")


def _dignity(pc: dict, planet: str) -> str:
    info = _planet_row(pc, planet)
    dig = _dignity_code(str(info.get("dignity") or info.get("sign_dignity") or ""))
    if dig:
        return dig
    sign = info.get("sign") or ""
    try:
        from astro_precompute import get_dignity
        return _dignity_code(get_dignity(planet, sign))
    except Exception:  # noqa: BLE001
        return ""


def _house(pc: dict, planet: str) -> Optional[int]:
    h = _planet_row(pc, planet).get("house")
    try:
        return int(h) if h is not None else None
    except (TypeError, ValueError):
        return None


def _strength_from_dignity_house(dig: str, house: Optional[int]) -> str:
    # Own/exalted in a dusthana is mixed (average), not fully weak.
    if dig in _STRONG and house in _DUSTHANA:
        return "average"
    if dig in _STRONG:
        return "strong"
    if dig in _WEAK or house in _DUSTHANA:
        return "weak"
    return "average"


def planet_strength(pc: dict, planet: str) -> str:
    """D1 (birth chart) strength only."""
    return _strength_from_dignity_house(_dignity(pc, planet), _house(pc, planet))


def planet_role(pc: dict, planet: str) -> str:
    lagna = (pc.get("lagna") or {}).get("sign") or ""
    stamped = _planet_row(pc, planet).get("functional_status") or ""
    if stamped:
        return _FUNC_WORD.get(str(stamped).lower(), "neutral")
    try:
        from astro_precompute import get_functional_status
        return _FUNC_WORD.get(get_functional_status(planet, lagna), "neutral")
    except Exception:  # noqa: BLE001
        return "neutral"


def _navamsha_sign(pc: dict, planet: str) -> str:
    info = _planet_row(pc, planet)
    nav = info.get("navamsha_sign") or info.get("d9_sign") or ""
    if nav:
        return str(nav)
    d9 = ((pc.get("divisional") or {}).get("D9") or {})
    if isinstance(d9, dict) and d9.get(planet):
        return str(d9.get(planet))
    for k in (pc.get("jaimini") or {}).get("karakas") or []:
        if k.get("planet") == planet and k.get("navamsha_sign"):
            return str(k.get("navamsha_sign"))
    return ""


def _d9_strength(pc: dict, planet: str) -> str:
    """Dignity strength in navamsha (D9) — sign quality only, not D9-lagna house."""
    if planet in ("Rahu", "Ketu"):
        return ""
    nav = _navamsha_sign(pc, planet)
    if not nav:
        return ""
    try:
        from astro_precompute import get_dignity
        dig = _dignity_code(get_dignity(planet, nav))
    except Exception:  # noqa: BLE001
        dig = ""
    if not dig:
        return ""
    if dig in _STRONG:
        return "strong"
    if dig in _WEAK:
        return "weak"
    return "average"


def _jaimini_pressure(pc: dict, planet: str) -> list[str]:
    """Jaimini stress flags for this planet (karakamsa perspective)."""
    flags: list[str] = []
    jm = pc.get("jaimini") or {}
    km = jm.get("karakamsa_sign") or ""
    pl_sign = _d1_sign(pc, planet)
    if km and pl_sign:
        try:
            from astro_precompute import house_from_lagna
            h = house_from_lagna(pl_sign, km)
            if h in _DUSTHANA:
                flags.append("secondary chart factors add some pressure")
        except Exception:  # noqa: BLE001
            pass
    # AK in dusthana from birth lagna is a known Jaimini caution for the soul-karaka.
    if jm.get("atmakaraka") == planet:
        h = _house(pc, planet)
        if h in _DUSTHANA:
            flags.append("a secondary chart factor adds pressure")
    return flags


def _ord(n: int) -> str:
    return f"{n}" + ("th" if 10 <= n % 100 <= 20
                     else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


def _level(s: str) -> int:
    return {"strong": 1, "average": 0, "weak": -1}.get(s, 0)


def confluence_for_planet(pc: dict, planet: str, d1_strength: str) -> tuple[str, str]:
    """Return (effective_strength_label, note).

    Keeps the main D1-based strength wording, but when D9/Jaimini disagree,
    switches chip tone toward mixed and attaches a short note.
    """
    notes: list[str] = []
    d9 = _d9_strength(pc, planet)
    jai_flags = _jaimini_pressure(pc, planet)

    if d9 and _level(d1_strength) >= 1 and _level(d9) <= -1:
        notes.append(f"weak in navamsha (D9)")
    elif d9 and _level(d1_strength) <= -1 and _level(d9) >= 1:
        notes.append(f"stronger in navamsha (D9)")

    notes.extend(jai_flags)

    if not notes:
        return d1_strength, ""

    # Show disagreement only when D1 looks good but secondary lanes do not,
    # or D1 looks poor but D9 rescues it.
    disagree = False
    if _level(d1_strength) >= 1 and (
            (d9 and _level(d9) <= -1) or any("pressure" in n or "Atmakaraka" in n for n in jai_flags)):
        disagree = True
    if _level(d1_strength) <= -1 and d9 and _level(d9) >= 1:
        disagree = True
    if jai_flags and _level(d1_strength) >= 0 and any("pressure" in n for n in jai_flags):
        disagree = True

    if not disagree:
        return d1_strength, ""

    note = "Mixed confluence: " + "; ".join(notes[:2])
    # Keep the D1 strength word (user can still see "strong") but mark mixed.
    return d1_strength, note


def _tone(role: str, strength: str, note: str) -> str:
    if note:
        return "mixed"
    if "supportive" in role:
        return "up" if strength != "weak" else "mixed"
    if role == "challenging":
        return "down" if strength != "strong" else "mixed"
    return "mixed"


def _bnn_note_for(pc: dict, planet: str, d1_strength: str,
                  bnn_detail: dict[str, str]) -> str:
    """When BNN rates a Vim lord differently from D1 strength, say so briefly."""
    v = (bnn_detail or {}).get(planet) or ""
    if not v:
        return ""
    if v == "amber" and _level(d1_strength) >= 0:
        return "BNN nadi: under pressure"
    if v == "good" and _level(d1_strength) <= -1:
        return "BNN nadi: stronger in the nadi read"
    return ""


def period_planets(pc: dict, *, paid: bool = False,
                   today: Optional[date] = None) -> list[dict[str, str]]:
    """Unique planets active in this chapter after confluence.

    Always: Vimshottari MD/AD.
    Paid: Yogini + Chara major/minor also vote — same planet merges into one
    chip with combined cycle tags (e.g. "sub-cycle · lunar · sign minor").
    BNN annotates MD/AD when the nadi vote differs.
    """
    today = today or date.today()
    vim = pc.get("vimshottari") or {}
    md = (vim.get("current_md") or {}).get("md_lord") or ""
    ad = ""
    for row in vim.get("current_md_antardashas") or []:
        if row.get("status") == "current":
            ad = row.get("ad_lord") or ""
            break
    # (planet, cycle short label, priority for merge sort)
    items: list[tuple[str, str, int]] = []
    if md:
        items.append((md, "main cycle", 0))
    if ad and ad != md:
        items.append((ad, "sub-cycle", 1))

    bnn_detail: dict[str, str] = {}
    if paid:
        try:
            import report_confluence as CF
            yog = CF.yogini_at(pc, today)
            yl = yog.get("lord") or ""
            yname = yog.get("yogini") or ""
            if yl:
                label = f"lunar · {yname}" if yname else "lunar cycle"
                items.append((yl, label, 2))
            jai = CF.jaimini_at(pc, today)
            if jai.get("lord") and jai.get("sign"):
                items.append((jai["lord"], f"sign major · {jai['sign']}", 3))
            if jai.get("antar_lord") and jai.get("antar"):
                items.append((jai["antar_lord"], f"sign minor · {jai['antar']}", 4))
            bnn_detail = (CF.bnn_period_vote(pc, md, ad).get("detail") or {})
        except Exception:  # noqa: BLE001
            yog = (pc.get("yogini") or {}).get("current_yogini") or {}
            yl = yog.get("lord") or ""
            if yl:
                items.append((yl, "lunar cycle", 2))

    # Merge by planet — one chip, combined clocks
    merged: dict[str, dict] = {}
    for planet, cycle, prio in items:
        if not planet:
            continue
        row = merged.get(planet)
        if row is None:
            merged[planet] = {"cycles": [cycle], "prio": prio}
        else:
            if cycle not in row["cycles"]:
                row["cycles"].append(cycle)
            row["prio"] = min(row["prio"], prio)

    vim_lords = {md, ad} - {""}
    out: list[dict[str, str]] = []
    for planet, meta in sorted(merged.items(), key=lambda kv: (kv[1]["prio"], kv[0])):
        strength = planet_strength(pc, planet)
        role = planet_role(pc, planet)
        strength, note = confluence_for_planet(pc, planet, strength)
        if planet in vim_lords and bnn_detail:
            bn = _bnn_note_for(pc, planet, strength, bnn_detail)
            if bn:
                note = f"{note}; {bn}" if note else bn
        cycle = " · ".join(meta["cycles"])
        line = f"{planet} — {strength} ({role})"
        if note:
            line = f"{line}. {note}"
        out.append({
            "planet": planet,
            "cycle": cycle,
            "strength": strength,
            "role": role,
            "note": note,
            "tone": _tone(role, strength, note),
            "line": line,
        })
    return out


def render_period_strip(pc: dict, *, paid: bool = False,
                        today: Optional[date] = None) -> str:
    rows = period_planets(pc, paid=paid, today=today)
    if not rows:
        return ""
    chips = "".join(
        f'<li class="pchip {_e(r["tone"])}">'
        f'<b>{_e(r["planet"])}</b>'
        f'<span>{_e(r["strength"])} · {_e(r["role"])}</span>'
        + (f'<em class="pchip-note">{_e(r["note"])}</em>' if r.get("note") else "")
        + f'<small>{_e(r["cycle"])}</small></li>'
        for r in rows)
    clocks = ("main cycle (Vimshottari)"
              + (", lunar (Yogini), sign-based (Chara), and nadi (BNN) on those lords"
                 if paid else ""))
    return f"""
<div class="planet-strip">
  <div class="ev-label">Planets shaping this chapter</div>
  <p class="sec-note">For your rising sign — D1 strength and functional role.
  Timing clocks considered: {clocks}.
  When navamsha (D9), Jaimini, or BNN disagree, the chip notes that mixed confluence.</p>
  <ul class="pchips">{chips}</ul>
</div>"""
